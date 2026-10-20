# ML Lane — Discovery Report (Custom Bidding Agent)

**Author:** Rodrigo Cunha (Principal ML Engineer) · **Date:** 2026-09-22 · **Phase:** Discovery · **Status:** Draft for review

> **Scope:** the ML lane only — the service that predicts, per candidate line item, the probability an impression leads to the advertiser's goal, plus the offline pipeline that builds and refreshes that model. Pacing (λ), the ingestor/processor, and the bid-decision service appear only at the ML boundary.
>
> Discovery-level: what we build, the main options with a lean, and what the client still needs to answer. **§4 (client questions) is self-contained and can be sent as-is.**

---

## 1. What we're building

The agent computes, per candidate line item:

```
Final Bid = λ × Max CPA × P(Goal Action | Impression)
```

We own **`P(Goal Action | Impression)`**: a calibrated probability, one per candidate, produced inside the agent's latency budget (the ad server enforces a 10ms end-to-end HTTP timeout; the ML step gets a slice). Two halves:

- **Online (hot path, ms):** take the request context + candidate line items, assemble features, score all candidates in one batch, return a probability per candidate. Fallback when the model or a feature is missing.
- **Offline (batch):** join served impressions to attributed conversions, train and calibrate the model, evaluate, version it in a registry, publish the model and precomputed features to the online path.

Today the client treats all advertisers as awareness (`bid = λ × Max CPM`, probability = 1). This lane enables performance bidding. MVP goal: a credible, calibrated probability for the first performance goal, built so more goals and better models can be added without redesign.

---

## 2. Design areas

Each area: current thinking → options → lean. Client questions are consolidated in §4.

### A. Prediction target & labels

- Goals (scope doc): **purchase** (top priority), **page view** (fallback), app install (post-MVP). Each line item optimizes one goal.
- Labels come from attribution, not raw pixels: a positive is a served impression (win log) matched to a conversion within an attribution window; a negative is a served impression with no attributed conversion. Web attribution runs through **the web-attribution provider** (`gold_kochava_*_day_attribution`), in-app through the MMP tables (`mobile_app_event_*_day_attribution`), at 7/14/30-day windows.
- Consequences: labels mature late (up to 30 days post-impression); attribution is an assumption, not ground truth (identity- and window-dependent, privacy-limited).
- **Lean:** one goal for MVP — the one with best label volume and business priority (likely purchase; page view if purchase is too sparse) — on one canonical window. Design for multiple goals later.

### B. Features & bid-time availability

- Two sources: **request-derived** (device, geo, app/site, content, segments, impression attributes, candidate metadata — free at bid time) and **precomputed** (history/heavy joins: line-item and creative performance, advertiser rates, contextual aggregates — computed offline, looked up fast).
- Cold start: new line items/creatives have no history and need a default.
- **Lean:** start with mostly request-derived features plus a small set of high-value precomputed features from a low-latency store. Bid-time work is lookups only.

### C. Online serving architecture

For tabular models, inference is microseconds; hot-path cost is hops, serialization, feature lookup, and runtime overhead. The choice is about minimizing hops.

| Option | Latency | ML iteration | Fit |
|---|---|---|---|
| Embedded in-process (Go agent, ONNX Runtime / Go GBDT) | Best (no hop) | Lower (Go ML tooling thin) | Go **monolith** |
| Co-located Go microservice (gRPC, same node/region) | Very good (one hop) | Medium | **Multi-service** |
| Triton Inference Server | Adds hop + heavy runtime | Good | Deep models on GPU |

- Model format: **ONNX** regardless — lets serving move (embed → Python → Triton) without retraining.
- This depends on the agent's **monolith (option 1) vs. multi-service (option 2)** choice from the SW-team benchmark.
- **Lean:** MVP is an ONNX tabular model, embedded or co-located in Go, matching the chosen agent topology. Reserve Triton for a later deep-model/GPU phase.

### D. Offline training infrastructure

- The client already runs AWS + Glue + MWAA/Airflow + Athena/Iceberg/S3 + Postgres (RDS); the bidder runs in its own AWS account and consumes client data across a boundary.
- Options: single large instance (simplest), SageMaker (AWS-native training + registry), Databricks (heavier, for large/Spark workloads), Ray (distributed Python), Glue (data prep, not model training).
- **Lean:** train on a single instance or SageMaker job; reuse the client's MWAA→Glue/Athena pattern for data prep. Escalate to Databricks/Ray only if data size demands it.

### E. Experiment tracking & model registry

- Datadog does not fit here (it is observability/APM — use it for serving monitoring). Tracking and versioned artifacts need a purpose-built tool.
- Options: self-hosted **MLflow** (portable), **SageMaker Model Registry** (AWS-native), external SaaS (W&B/Comet/Neptune).
- **Lean:** self-hosted MLflow or SageMaker Model Registry, decided with the training-infra choice (D); Datadog for online monitoring.

### F. Data quality & validation

- Bids are real money and labels are attribution-derived, so we validate before data reaches training or serving: schema/type, null/coverage, label coverage and attribution freshness, feature drift, and train/serve consistency (features computed the same way in both paths).
- **Lean:** a lightweight validation step in the offline pipeline plus serving-side monitoring of feature nulls and prediction distributions. Proportionate for MVP.

### G. Model lifecycle & operationalization

- Retraining cadence: configurable (scheduled and/or on demand). Late-maturing labels mean recent data is not fully labeled; training windows must account for this.
- Deployment: publish a version to serving with an offline eval gate before live traffic, and rollback. Shadow/canary can follow MVP.
- Monitoring: latency, prediction distribution, feature nulls, and calibration drift (predicted vs. actual conversion rate).
- **Lean:** orchestrate with MWAA; model versions flow registry → serving through an eval gate; monitor in Datadog.

### H. Calibration & fallback (cross-cutting)

- Calibration: the output is multiplied by dollars (`Max CPA × P`), so it must be a true probability, not a ranking score. Raw model scores are not calibrated — tree models are typically over-confident, and downsampling negatives (common for rare conversions) shifts the base rate and inflates scores. Two corrections, fit offline on a held-out set and baked into the served artifact:
  - **Base-rate correction:** undo the class-balance shift from negative downsampling by rescaling predicted odds by the negative keep-fraction, mapping predictions back to the true event rate. Closed-form; skipped if negatives are not downsampled.
  - **Post-hoc calibrator:** fit Platt scaling (logistic) or isotonic regression to align scores with observed frequencies; apply after the base-rate correction.
  Track calibration live (reliability diagram / ECE, predicted vs. actual conversion rate), on a lag due to attribution windows.
- Fallback: when the model or a feature is unavailable (cold start, timeout, missing feature), return a safe default probability so the agent still responds within 10ms.

---

## 3. Assumptions until told otherwise

Defaults that let work proceed; each is revised on client input.

1. MVP model is tabular GBDT on CPU, exported to ONNX.
2. MVP targets one goal (purchase, or page view if purchase labels are sparse), one attribution window.
3. Labels are the client's attributed-conversion datasets (web-attribution provider for web / MMP for app), consumed from curated outputs, not raw tables.
4. The ML service returns `P(Action)`; the `× Max CPA` multiply lives in the bid-decision service (see §4 Q13).
5. Serving co-locates with the agent in the same region/node; topology follows the SW-team benchmark.
6. Training starts small (single instance / SageMaker) reusing the client's MWAA→Glue/Athena data prep.
7. Tracking/registry is self-hosted MLflow or SageMaker; Datadog for serving monitoring.
8. Scores are calibrated post-hoc (Platt or isotonic), with base-rate correction if negatives are downsampled, and the calibrator is baked into the served artifact.

---

## 4. Open questions for the client

*Self-contained — copy and send. **Top blockers: Q1, Q2, Q7.***

**Data — highest priority**
- **Q1 — EDA data sample:** Can you share a real (sanitized) sample of the impression-level table that would feed the model — one row per served impression/candidate, with the request/context features, delivery/auction fields (bid, win, spend), campaign/ad-set/creative config, and the outcome/attribution label? (This is the "impression-level training dataset" in the data-context doc; a sample lets us start EDA.)
- **Q2 — Data-engineering ownership:** For training data and online features, will the client's pipelines deliver ready **joined** datasets (impression ↔ attribution ↔ config), will we get raw access and **build the joins ourselves**, or a hybrid? In particular, who owns the impression→conversion→config joins and the client-UUID ↔ the DSP-ID identity mapping?
- **Q3 — Delivery mechanism & cadence:** How will each dataset reach the bidder account (curated export to S3, Lake Formation share, direct Athena, or event stream/API), and how often will it refresh?
- **Q4 — Feature freshness:** For each feature category, how fresh can the data be — near-real-time, hourly, or daily?
- **Q5 — Real bid-request payloads:** Can you provide representative real bid-request payloads for premium video/TV? The samples we have are banner examples from a tool.

**Prediction target & labels**
- **Q6 — First goal:** Which goal should the first model optimize — purchase or page view — and roughly how many labeled examples exist for each?
- **Q7 — Attribution label:** Which attribution window (7, 14, or 30-day) and method (click-through vs. view-through) should define the training label, and is there a single canonical choice?
- **Q8 — Attribution coverage:** In practice, what share of conversions can be matched back to an impression, and how are unmatched or privacy-limited conversions handled?
- **Q9 — CVR baselines:** Do you have existing conversion-rate baselines (overall and by segment) we can calibrate against and use as a benchmark?

**Serving & latency**
- **Q10 — Throughput & candidates:** What request throughput should we expect (typical and peak), and how many candidate line items usually arrive per request?
- **Q11 — ML latency budget:** Of the 10ms end-to-end budget, how much is allocated to the ML prediction step?
- **Q12 — Agent topology:** Is the agent being built as a single Go service (monolith) or multiple services, and when will the benchmark decide?
- **Q13 — GPU:** Is GPU available in the bidder account, or should we assume CPU-only for the MVP?
- **Q14 — Max CPA:** Will the advertiser's Max CPA be available at bid time, and where does it come from (the request, or a config/ranking service)?

**Infrastructure & environment**
- **Q15 — Training infrastructure:** What training infrastructure is available or preferred in the bidder account (a single large instance, SageMaker, Databricks, Ray)?
- **Q16 — Stack reuse:** Can we reuse the client's existing MWAA/Glue/Athena stack for data prep and orchestration, or should we stand up our own?

---

## 5. Dependencies & risks

- **Data-engineering ownership & access** (Q2, Q3) — critical path; no training data or online features until resolved.
- **EDA data sample** (Q1) — needed to explore the data before committing to a design.
- **Attribution label definition** (Q7) — defines what the model predicts; blocks label construction.
- **Serving topology** (Q12) — owned by the SW-team benchmark; our serving choice depends on it.

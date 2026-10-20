# CLAUDE.md — Client ML Discovery (Custom Bidding Agent)

This project is the **ML-lane discovery work** for the **client's custom bidding agent**. Author: Rodrigo Cunha, Principal ML Engineer (Sigma Software). Phase: **discovery**.

## Anonymization (standing rule)

This repo never names the client, its parent company, or its vendors (the third-party ad server, the web-attribution provider, the upstream DSP) — all are referred to generically ("the client", "the ad-server vendor", …). Two exceptions: literal data identifiers (table/database names in backticks) stay verbatim, and client-original files (`docs/batch_*/` outside the `md/` folders, and all `.docx`) are never modified. **Every new client doc reparsed into a `md/` folder gets this anonymization pass before anything cites it.**

---

## What the system is

The client is building a **custom real-time bidding agent**, co-located with the third-party ad server, that receives protobuf bid requests (carrying an array of eligible candidate line items) and returns a bid per candidate within the ad server's **10 ms end-to-end HTTP timeout**. The bid is:

```
Final Bid = λ × Max CPA × P(Goal Action | Impression)
```

Four logical services: **Bid Ingestor/Processor**, **Discount Pacing (λ)**, **ML Prediction (Expected Value / Ad Ranking)**, **Bid Decision/Response**.

Ad sets will carry two new fields (batch-02 ML report): **`bidding_strategy`** ∈ {`max_cpm`, `goal_cpa`, `lowest_cost` ("auto bid")} and **`optimization_goal`** — the action to predict, which selects the model (`impressions` needs none, `P = 1`). Initial models: **Page View and Purchase**. Today all the client's advertisers are effectively **awareness** (`bid = λ × Max CPM`, probability = 1). This project unlocks **performance** (CPA) bidding.

## Our lane

We own the **ML Prediction service = `P(Goal Action | Impression)`** — a *calibrated* per-candidate probability — plus the offline pipeline that builds and refreshes it. Pacing (λ), the ingestor, and the bid-decision service are other lanes; we touch them only at the ML boundary. The client requires at least `P(Action)` from the ML service and leaves probability-vs-EV as a technical design decision — ADR-0001 (return the probability) stands. Within the ad server's 10 ms end-to-end budget, the ML Prediction step's own latency target is a firm **~3 ms p99** (our budget allocation, not an initial figure).

- **Online (hot path, ms):** assemble features, score all candidates in one batch, return a probability per candidate, with a fallback when the model or a feature is missing.
- **Offline (batch):** join served impressions to attributed conversions, train + calibrate, evaluate, version in a registry, publish model + precomputed features.

## Standing decisions & leans (see `adr/`)

- **ADR-0001 (Accepted, amended):** the ML service returns the **probability `P(Action)`**; the bid-decision service applies `× Max CPA`. (The client's docs name the service in EV terms — "Expected Value formulation" — while their formulas multiply downstream; batch-02 leaves the interface explicitly open, so ADR-0001 is our proposal.)
- **ADR-0002 (Accepted, amended):** MVP serving is a **tabular GBDT exported to ONNX, on CPU, embedded in the Go agent** (pure library, no server mode — settled); Triton deferred to a later deep-model/GPU phase.
- **ADR-0003 (Accepted, amended):** **calibration is mandatory** and versioned with the model as a matched pair, baked into the served artifact (post-hoc Platt/isotonic + base-rate correction if negatives are downsampled); amended 2026-10-15 to allow per-window and (future) per-advertiser parameterized calibration within the same matched-pair rule.
- **ADR-0004 (Proposed, blocker):** the **attribution window + method** that defines the training label — needs client input.
- **ADR-0005 (Proposed, blocker — DE lane):** the **cross-boundary data-access / data-engineering ownership** pattern — needs client input; owned by the Data Engineering lane. The ML lane treats the five curated datasets as a given and states requirements on them.
- **ADR-0006 (Accepted, discovery — revisable):** the served artifact is the **self-contained pipeline** — preprocessing, model, and calibration in one ONNX file; no preprocessing or postprocessing executes outside the graph (feature assembly and the Redis lookup are Go steps around it).

Two model-agnostic facts to hold onto: **labels come from attributed conversions** (web-attribution provider for web / MMP for app; 7/14/30-day window tables documented in batch-01, a 1-day variant stated available in the batch-02 ML report — to confirm; late-maturing) and **serving is Python-offline, Go-online, with ONNX as the bridge**.

## Stack split

- **Offline → full Python** (training, calibration, feature engineering, EDA, evaluation).
- **Serving (hot path) → Go, no Python.** Go loads the ONNX artifact in-process via `onnxruntime_go` — the lean, since the artifact is the full pipeline (ADR-0006) and the pure-Go `leaves` scorer, though benchmarked fastest on bare trees, cannot run in-graph preprocessing/calibration. **Triton** stays deferred (ADR-0002). The model is trained in Python but **exported to ONNX**, which is the language bridge.

## Environment (client)

The client runs on **AWS**: Postgres (RDS), S3, Athena, Iceberg, Glue, MWAA/Airflow, Lake Formation, Datadog, Secrets Manager/KMS. **Databricks runs the ML workloads** (client-confirmed); within it, compute, MLflow tracking with the Unity Catalog registry, and Delta as the table format are **our directed picks**, not client-mandated. The **bidder most likely runs in its own AWS account** (client: "most likely"; an alternative client doc frames it as a Terraform boundary in shared infra) and consumes the client's data **across an account boundary** either way. Web attribution → a **web-attribution provider**; in-app → **MMP** trackers. Identity mapping: client UUIDs ≠ the upstream DSP's integer IDs (`external_id`/`alt_id` bridge). Compliance: an **AI-use annex** forbids AI systems not provided by the client's parent company for the work without written approval.

## File map

| Path | Contents |
|---|---|
| `reports/` | Delivered, frozen reports — **never update them.** `discovery_report/ML_Lane_Discovery_Report.md` (+ `.docx`), delivered 2026-09-22; its Q1–Q16 and leans are that date's snapshot; the living record is `DISCOVERY_SUMMARY.md` + `adr/` |
| `DISCOVERY_SUMMARY.md` | Living knowledge base — client facts vs. our analysis |
| `design_docs/OPEN_QUESTIONS.md` | The consolidated register of every open question — client / EDA-gated / team / serving-side — each referencing its source docs |
| `design_docs/CLIENT_QUESTIONS.md` | The client-facing subset, self-contained and sendable |
| `adr/` | ML-lane ADRs (MADR-lite): ADR-0000 meta + 0001–0006 + `template.md` |
| `design_docs/` | Offline ML platform design (ETL, training, hot-feature pipelines on AWS + Databricks); design docs only, see its `CLAUDE.md` |
| [ml_serving](https://github.com/cunha-sigma/ml_serving) (external repo) | The MVP ML-serving Go library (ONNX artifact + manifest, rollout config, hot-feature mirror, decision logs). No local copy — always link the GitHub repo |
| [ml_serving_bench](https://github.com/cunha-sigma/ml_serving_bench) (external repo) | Frozen serving-latency benchmark (engines `leaves` + ORT, stage-placement arrangements, serving report). No local copy — always link the GitHub repo |
| `docs/` | Client input: `batch_01/` (initial doc set) + `batch_02/` (2026-10: `client_reports/` + Olena's `testing/` docs); each batch has an `md/` conversion folder |
| `scratchpad.md` | Living worklog / current status |

## Team

Rodrigo Cunha (Principal ML Eng — this lane) · Matheus Bergmann (Senior ML Eng) · Illia Slobozhanin (Principal Data Eng) · Augusto Pietroski (Senior SW Dev — ingestor/pacing benchmarks, monolith-vs-microservices) · Yuri Mednis (Lead SW Dev) · Olena Ozerova (Principal QA).

## Conventions

- **Python** for offline/ML code (type hints on signatures); **Go** for the serving hot path.
- **Architecture decisions are ADRs** in `adr/` (MADR-lite). Add ADRs by agreement, only for load-bearing decisions.
- Keep the discovery report **direct and non-verbose**; client questions must read as real, self-contained questions.
- Cloud-specific choices stay open until the relevant ADR is Accepted.

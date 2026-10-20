# Client Custom Bidding Agent — Discovery Summary

**Purpose:** Durable, single-file knowledge base for the client custom-bidding-agent project, ML-lane focused. Consolidates client-provided facts and our team's analysis so context survives across sessions and people.
**Date:** 2026-09-22 · **Updated:** 2026-10-20 (design_docs set complete, 00–09; final whole-design audit) · **Status:** living summary

> **How to read this file.** Two top-level parts are kept strictly separate:
> **Part 1 — Client-provided facts** (what the client docs state) and
> **Part 2 — Our analysis & working decisions** (what our team has reasoned or leaned, from the ML Lane Discovery Report and ADRs).
> Never treat Part 2 as client-confirmed. Open questions to the client live in §2.4.

---

# Part 1 — Client-provided facts

*Source: the client documents under `docs/batch_01/md/` (initial doc set) and `docs/batch_02/md/client_reports/` (2026-10 background reports, §1.9). These are statements from the client, not our conclusions.*

## 1.1 Project overview

- The client runs a self-service platform for premium TV/streaming advertising (per the project brief, which is marked outdated; no current doc restates it). It is building a **custom bidding agent** for real-time bid decisioning, to gain more granular, dynamic bid control than the ad server's current process allows.
- The agent is **co-located with the ad server bidding infrastructure** and speaks the ad server's **protobuf interface**. It ingests a bid request + the array of eligible line items/creatives (no line-item retrieval needed), decides, and returns a response.
- **Bidding formula (performance advertisers):**
  ```
  Final Bid = λ (pacing discount) × Expected Value
  Expected Value = Max CPA × P(Goal Action | Impression)
  ```
  - **Max CPA** — advertiser-defined max cost per desired action, collected in the client's Ads Manager.
  - **P(Goal Action | Impression)** — predicted probability the impression yields the desired action (the client's ML models).
  - **λ (pacing lambda)** — per-line-item discount from comparing expected vs. actual spend-to-date; recomputed each pacing cycle; does **not** need to run in the synchronous bid path.
- **Awareness vs. performance:** Awareness campaigns keep CPM goals, modeled as `P(Impression | Impression) = 1`, so only λ is dynamic. **Today the client does not offer cost-per-action bidding — all advertisers are effectively "awareness."** This project enables performance bidding.
- **Future:** "auto bid" (no Max CPA; bid modulated entirely by λ, equivalent to a very high Max CPA) enabled via a line-item flag once the services exist.

## 1.2 The four services and request flow

The agent is designed as logically separate components so pacing, prediction, and bidding evolve independently (the SW-team benchmark doc stresses these are logical boundaries, **not** mandated separate deployments):

| # | Service | Responsibility |
|---|---|---|
| 2.1 | **Bid Ingestor / Processor** | Entry point. Deserialize/validate the ad server protobuf, extract candidates + request context, orchestrate downstream calls, manage lifecycle within latency, handle invalid requests, log/observe. |
| 2.2 | **Discount Pacing (λ)** | Periodically compute per-line-item λ from expected vs. actual spend-to-date; expose latest λ via low-latency lookup; configurable refresh; safe behavior when λ is stale/missing. Does not necessarily need to run in the synchronous request path (client wording). |
| 2.3 | **ML Prediction (Expected Value)** | Return `P(Action)` per candidate line item. New models/goals must be addable without changing bid-processing architecture. Latency approaches suggested: in-memory inference, precomputed features, low-latency serving, or precomputed value lookups. |
| 2.4 | **Bid Decision / Response** | Combine Max CPA, `P(Action)`, and λ into `Final Bid = λ × Max CPA × P(Action)`; select candidate(s); build a valid the ad server `BidAgentResponse`. |

- **Request flow:** the ad server → Ingestor → (Pacing lookup ‖ ML prediction) → Bid Decision → response. (The end-to-end diagram is `image1.png`, which we cannot render; its labels are client-infra components, not the agent's internal flow.)
- **External contract (per the SW-team benchmark doc):** the ad server sends **HTTP POST** with a protobuf `bid.BidAgentRequest`; agent returns **HTTP 200** with `bid.BidAgentResponse` or **HTTP 204** (no bid). The 10 ms end-to-end latency is treated there as a strict response timeout (the client-authored docs state it as an *initial target*); same-AWS-region deployment is the ad server's recommendation. Processing budget must leave room for transport. Bid prices are **integer micros per impression** (e.g., 0.8 × $20 × 0.001 = $0.016 = 16,000 micros = $16 CPM).
- Schemas are the DSP's OpenRTB (`beeswax-api`: `request.proto`, `adcandidate.proto`). Candidates carry line-item/creative IDs, bidding settings, frequency caps, fees.

## 1.3 Monolith vs. multi-service benchmark (SW team)

The SW team proposed benchmarking two topologies (pick the simplest that meets latency/throughput/reliability with headroom):
- **Approach 1 — Distributed Go microservices** over gRPC (processor fans out to pacing + prediction; bid calc stays with processor for the comparison). Compare unary vs. streaming; measure serialization, network, queueing.
- **Approach 2 — Modular in-process Go app** (one deployable, four components behind an orchestrator, no internal network). Four execution variants: (A) sequential, (B) per-request goroutines, (C) persistent worker pools, (D) direct pacing snapshot read + inference worker pool.
- The initial prediction interface **should return probabilities explicitly**; EV and bid are computed once downstream.
- Benchmark payloads are official DSP fixtures (`sample_bid_request_1.txt`), maintained as protobuf text, compiled to binary. Three bundled payloads are **banner examples (1–2 candidates, ~1.1–2.1 KB binary)** — explicitly **not verified client production traffic**. Payload matrix scales candidates (1→500) and creatives; video profiles planned but need real samples.

## 1.4 Data & labels

- **Prediction target uses attribution, not raw pixels** (client: measurement and attribution data provides the labels and outcomes for model training). The positive/negative construction — positive = served impression matched to an attributed conversion within the window, negative = served impression with none — is **our** label design (ADR-0004), resting on the unconfirmed wins-only-universe assumption.
- **Web attribution → the web-attribution provider**; **in-app → MMP (mobile measurement partner) trackers**. Windows: **7 / 14 / 30 day** tables documented in the batch-01 data models; the batch-02 ML report states a **1-day** variant is also available ("one/fourteen/thirty day are available", plus its `PIXEL_PURCHASE_1_day` example and its train-on-1-day question) — 1-day table to confirm with the client.
- **Late-maturing labels:** attribution windows stay open for days, so recent data is only partially labeled and conversions arrive after delivery.
- **Goals (scope doc, with the client's own hedges):** **Pixel Purchase** ("likely the top priority goal we'd want to ship"), **Page View** ("likely the p0 goal" if purchase isn't possible), **App Install** (out of MVP scope), plus future optimization events. (Batch-02 later makes Page View and Purchase co-priorities — see §1.9 and contradiction #5.)
- **Key tables:**
  - `gold_kochava_{seven,fourteen,thirty}_day_attribution` — web-attributed conversions (query/reporting layer; keys: conversion_id, enhanced_pixel_id, ad_id, adaccount_id).
  - `mobile_app_event_{7,14,30}_day_attribution` — app-attributed conversions (keys: conversion_id, app_tracker_id, ad_id; has revenue, impression_id).
  - `raw_performance_data` / `win_logs` — raw DSP delivery/win-log data in S3 (auction, bid, cost, supply, device, geo, content, model metadata). **Downstream integer IDs, not client UUIDs.**
  - `performance_report_pipeline_merged` — hourly aggregate per `ad_id × hour` (impressions, clicks, conversions, spend, ctr/cpa/cvr, video quartiles).
  - Supporting: `kochava_conversion_data`, `attributed_conversion_data`, `raw_attributed_conversion_data`, `app_events_conversion_data`, `raw_performance_data_kochava`, raw `kochava`.
- **Identity mapping (critical):** the client stores its own **UUIDs**; for objects that also exist in the DSP, the DSP ID goes in the client's `external_id` and the client UUID goes in the DSP's `alt_id`. Raw DSP logs carry **integer** `campaign_id`, `line_item_id`, `creative_id`, `account_id` — **must be mapped** via `external_id`, never treated as UUIDs. Unified bidder datasets must expose client UUID, DSP ID, and raw-log ID as separate, clearly named fields.
- **Entity hierarchy:** organization → adaccount → campaign → **adset (≈ DSP line item, the primary delivery config object: bid, budget, dates, pacing, targeting, tracker links)** → ad → creative → media. `campaign.objective_type` ∈ {web_conversions, awareness, app_promotion}; the `adset_type` enum currently **includes video** (the data models say "includes", not "only"). Web measurement uses **enhanced_pixel** (now via the web-attribution provider); app uses **app_tracker** (MMP). Admin `adset_delivery_override` takes precedence over defaults.

## 1.5 Infrastructure & environment

- **The client runs in AWS** inside a private VPC (VPC/subnets managed by the ad server, imported into client Terraform).
- **Client data/warehouse stack:** Postgres (RDS, source of truth for config/entity state), S3 (raw + semi-processed), Athena (query), Apache Iceberg (table format), Glue Catalog + Lake Formation (governance), **Glue + MWAA/Airflow** for data jobs.
- **App compute:** ECS/Fargate; deploys via CodePipeline/CodeBuild/CodeDeploy/ECR; all IaC in Terraform (`dev`/`stg`/`prod` roots).
- **Secrets/keys:** AWS Secrets Manager + KMS. **Observability:** CloudWatch alarms, Slack alerts, **Datadog APM**.
- **The bidder most likely runs in its own AWS account** (the client's wording is "most likely"; another client doc frames the bidder instead as a Terraform-ownership boundary that may consume shared VPC/Postgres/Athena — the topology is not final), consuming client data **across an account boundary** either way. The client remains source of truth for config, eligibility, attribution, and warehouse outputs; the bidder owns model execution, decisioning, experimentation. Cross-account sharing via cross-account IAM, Lake Formation sharing, S3 replication/export, event streams, or APIs. **Bidder infra expectation (UA_Infra doc): a dedicated EKS cluster, ECR, pipeline, IAM roles, security group, private subnets, CloudWatch, Secrets Manager.** RDS access = add bidder SG to RDS ingress on 5432; Athena access = workgroup + Glue reads + S3 results + Lake Formation grants.
- **Bidder should consume curated client outputs, not raw internal tables.** Proposed dataset split: delivery-control feed, impression-level training dataset, attribution-labels dataset, aggregate performance dataset, bidder-response dataset.
- **Data-cadence tiers (the client's proposed expectations for the curated feeds, not live cadences):**
  | Tier | Contents |
  |---|---|
  | Immediate / event-driven | eligibility changes: pause, archive, spend lock, delivery disable, budget stops, critical override changes |
  | Frequent / near-real-time | active delivery settings, bid config, targeting eligibility, deals, creative eligibility |
  | Hourly | delivery metrics, spend, impressions, clicks, win rate, bid/win diagnostics |
  | Daily | attributed conversions, finalized reporting, training labels, feature snapshots |
  | Weekly / backfill | large historical training sets, attribution reprocessing, feature rebuilds, model experiment datasets |

  The delivery-control feed's target cadence and implementation are explicitly still to be determined (client).

## 1.6 Compliance

- **AI-use annex (contractual):** AI systems not provided by the client's parent company may not be used for the work without prior **written approval from Sigma**, and AI systems in use must be disclosed. The annex is in the doc set (`docs/batch_01/md/AI annex for Comcast.md`). Practical effect: likely rules out external ML SaaS unless approved.
- Data models flag many **privacy-sensitive** fields (`platform_device_ifa`/`platform_device_idfa`, `ip_address`/`ipv6_address`/`impression_ip_address`, `hhid`, `user_id`, `user_email`, device ids) and consent signals (`is_gdpr`, `is_gdpr_consented`, `gdpr_consent_string`, `us_privacy`, `dnt`, `lmt`) requiring privacy-aware handling and retention rules.

## 1.7 Non-functional / success criteria (client-stated)

- < 10ms end-to-end HTTP; horizontal scaling; health checks; controlled deploy/rollback.
- Monitor: total/processed requests, response rate, e2e + per-component latency, errors/timeouts, candidates evaluated, `P(Action)`/λ/Max CPA/EV/final bid used, win/loss, spend/pacing; down-sampled decision-level logging to reconstruct any bid.
- Phase-1 success = reliably ingest/parse the ad server requests, evaluate candidates, obtain a probability/value signal, retrieve λ, combine with Max CPA, compute final bid, respond within latency, deploy/scale reliably, and upgrade components independently.

## 1.8 Process

- **Technical debt process:** logged in a register (Description / Identified / Owner / Estimate / Priority / Status / Jira ID / Comments), reviewed at least biweekly (Sigma DSP team: Monday calls), promoted to Jira when scheduled. The provided register is an empty template.

## 1.9 Batch-02 client reports (2026-10)

*Source: `docs/batch_02/md/client_reports/`. Two background reports from the client. The ML one is our lane; the pacing one is reference only (pacing is another lane).*

### ML Service Background (2026-10-11)

- **Bidding strategies via two new ad set fields** (do not exist yet in the ad set data model): `bidding_strategy` ∈ {`max_cpm`, `goal_cpa`, `lowest_cost` (= "auto bid")} and `optimization_goal` — the action the advertiser wants to drive, hence which model to consult (the client lists eventual support for `impressions`, `PIXEL_PAGE_VIEW`, `PIXEL_PURCHASE`, and `app_installs`). Together they determine whether inference is needed, which model is used, and how `max_bid` is interpreted.
- **Expected value per impression, by strategy** (`Final Bid = λ × EV` for all three):

| Strategy | EV per impression | Model use |
|---|---|---|
| `max_cpm` | `max_bid / 1,000` | none — effective goal is impressions, `P = 1`; deterministic non-ML path |
| `goal_cpa` | `max_bid × P(Action)` | model selected by `optimization_goal` |
| `lowest_cost` | `Internal CPA Value × P(Action)` | same goal-specific model; no advertiser CPA limit — a high internal CPA value scales the bid and λ finds the level that spends the budget |

All equations are per impression; a CPM bid representation multiplies by 1,000. Units must stay consistent across config, model output, EV calculation, and bid response. The goal-CPA behavior is an expected-performance objective, "not a guarantee of observed CPA in every reporting period"; the evaluation window and the treatment of fees "remain to be defined".

- **Attribution window may become advertiser-facing config:** e.g. `optimization_goal = PIXEL_PURCHASE_7_day` vs. `PIXEL_PURCHASE_14_day`, or a separate ad set column. Directly reshapes the ADR-0004 framing: the window may be a product dimension rather than one canonical choice.
- **Initial model priorities: Page View AND Purchase**, both supporting goal_cpa and lowest_cost. New goals (app installs/purchases, lead generation) must be addable later without replacing the core bidding architecture.
- **Sparse-signal advertisers are a hard requirement:** the approach cannot depend on every advertiser having enough conversions for an advertiser-specific model; it must serve new/low-signal advertisers and incorporate advertiser-specific information as it arrives. Shared models vs. an advertiser-specific calibration layer is explicitly open for discussion.
- **ML interface left open:** the service "does not necessarily need to produce the full EV but must at least provide the goal p(Action)" — probability vs. EV vs. both is a technical design decision; applying pacing and building the response stays with the Bidding Service. Consistent with ADR-0001.
- **Latency framing:** the <10 ms target is the full real-time path, not ML alone; ML fits its allocated portion. In-memory inference, precomputed features, low-latency serving, and precomputed lookups are named as options, not a selected architecture.
- **Required logging:** prediction, value input, expected value, and λ used per bid, so any decision can be reconstructed. Models and new optimization goals must evolve without redesigning request processing.
- **Training datasets named:** auctions and bid logs in `vir-prod-uaadsmanager-reporting-db` (`auction_us_{east,west}`, `bid_logs_us_{east,west}`); win logs in `ua-data-jobs-prod-reporting.win_logs` (batched) and `vir-prod-uaadsmanager-reporting-db.silver_win_logs_stream` (streamed); pixel conversions `silver_kochava_events` + `gold_kochava_seven_day_attribution` ("one/fourteen/thirty day are available" — the 1-day variant is new vs. the batch-01 data models); app conversions `bronze_mobile_app_events` + `gold_app_events_seven_day_attribution` (same window note). The report names only the two databases; the query engine is unstated (Athena is our inference from the client's stack).
- **Client's open ML questions:** which attribution windows to offer per goal and how to model them (separate models per window vs. train on 1-day and up-calibrate); sparse-signal/new-advertiser handling; calibration and evaluation per goal incl. launch-readiness criteria; features available at bid time vs. precomputed, the ML share of the latency budget, multi-candidate evaluation, and fallback behavior; whether the interface returns probability, EV, or both, and how models are tested/deployed/rolled back.

### Pacing Service Background (2026-10-07) — reference only, other lane

- Defines discount pacing **λ** (bid-price multiplier) vs. probabilistic pacing **α** (auction inclusion rate); proposes a hybrid start where the client Pacing Service computes λ (even curves first) and the ad server's Pacing-as-a-Service keeps α. Kept only for the λ semantics used in the bid formula; the pacer is not our scope.

---

# Part 2 — Our analysis & working decisions

*Source: `reports/discovery_report/ML_Lane_Discovery_Report.md` (Rodrigo Cunha, 2026-09-22, delivered and frozen), the `adr/` set, and the team's testing docs (`docs/batch_02/md/testing/`, §2.7). These are our team's reasoning and leans — not client-confirmed. Open questions are in §2.4.*

## 2.1 What we own

The **ML lane only**: the service that returns a **calibrated `P(Goal Action | Impression)`** per candidate within the ML slice of the 10ms budget, plus the offline pipeline that builds/refreshes it. Two halves:
- **Online (hot path, ms):** assemble features, batch-score all candidates, return a probability each; fallback on missing model/feature.
- **Offline (batch):** join served impressions to attributed conversions, train + calibrate, evaluate, version in a registry, publish model + precomputed features to serving.

MVP goal: credible calibrated probabilities for the two initial goals (Page View, Purchase), extensible to more goals/models without redesign.

## 2.2 Working leans (Discovery Report §2)

| Area | Lean |
|---|---|
| Target & labels | **Page View and Purchase both MVP goals** (batch-02); **one global model per goal, single window each for now**, extending to one model per (goal, window) once the client's offered windows firm up; advertisers as features (no per-advertiser models — client's sparse-signal constraint). Window may become advertiser-facing config; up-calibration from a shorter window kept as a conditional alternative (ADR-0004). |
| Features | Mostly **request-derived** features (free at bid time) + a small set of high-value **precomputed** features from a low-latency store; bid-time work = lookups only. Cold-start needs defaults. |
| Serving architecture | **ONNX tabular GBDT on CPU** for MVP, **embedded in the Go agent** — settled on the serving side as a pure Go library the agent imports (no server mode, no gRPC/HTTP listener). The agent's own monolith-vs-multi-service topology is still the SW-team benchmark's question, but it no longer affects the ML embedding choice. **ONNX regardless**, so serving can move (embed → Python → Triton) without retraining. **Triton deferred** to a later deep-model/GPU phase. |
| Training infra | **Databricks (client-confirmed, direct client knowledge — postdates the batch-01 docs):** workloads/compute, Delta as table format, Unity Catalog. Orchestration via MWAA/Airflow; whether we reuse the client's instance or run our own is open. Offline platform design in `design_docs/`. |
| Tracking & registry | **MLflow with Unity Catalog on Databricks** (experiment tracking + model registry). Datadog is for serving monitoring, not tracking. |
| Calibration (cross-cutting) | **Required** — output is multiplied by dollars, so it must be a true probability. Two corrections fit offline on held-out data and **baked into the served ONNX artifact**: (1) **base-rate correction** to undo negative-downsampling class shift (closed-form; skip if not downsampling); (2) **post-hoc calibrator** (Platt / isotonic) applied after. Calibrator is **versioned with the model as a matched pair**. Track live via reliability diagram / ECE on an attribution lag. Future, not MVP: **per-advertiser calibration** for data-rich advertisers — calibration parameters keyed by advertiser id as an in-graph lookup (Gather + global default row), fit as a group-by with shrinkage toward the global fit, gated by a minimum-volume eligibility threshold; per-advertiser calibration error is a standard evaluation cut from MVP on, to detect when this layer earns its place. Per-window calibrators use the same mechanism on the artifact axis (same trees, different calibrator per window). |
| Data quality | Lightweight offline validation (schema, nulls/coverage, label coverage, attribution freshness, drift, train/serve parity) + serving-side monitoring of feature nulls and prediction distribution. |
| Lifecycle | Configurable retraining cadence; training windows must account for late-maturing labels; publish via **offline eval gate → serving**, with rollback; shadow/canary/A-B designed in (design_docs 06), activation per rollout policy; orchestrate with MWAA; monitor in Datadog. |
| Fallback | On missing model/feature/timeout/cold-start, return a safe default probability so the agent still answers in 10ms. |

## 2.3 Assumptions until told otherwise (Discovery Report §3)

1. MVP model = tabular GBDT on CPU, exported to ONNX.
2. Two initial goals (Page View, Purchase), a single window per goal for now; one model per (goal, window) as the end state.
3. Labels from the client's curated attributed-conversion datasets (web-attribution provider for web / MMP for app), not raw tables.
4. **ML service returns `P(Action)`; the `× Max CPA` multiply lives in the Bid Decision service** (see discrepancy below).
5. Serving co-located with the agent (same region/node); topology follows the benchmark.
6. Training and data workloads run on Databricks (client-confirmed); orchestration via MWAA/Airflow.
7. Tracking/registry = MLflow with Unity Catalog on Databricks; Datadog for serving monitoring.
8. Scores calibrated post-hoc (Platt/isotonic) + base-rate correction if downsampling; calibrator baked into the served artifact.

## 2.4 Open questions (moved)

The maintained lists now live with the design:
`design_docs/OPEN_QUESTIONS.md` is the consolidated register of every
open question (client / EDA-gated / team / serving-side, each with its
sources), and `design_docs/CLIENT_QUESTIONS.md` is the client-facing
subset, phrased to send. The delivered report's Q1–Q16 (2026-09-22)
remains a frozen snapshot with its own numbering. Refer to questions
**by topic, never by number**. The historical list below is kept only
for the settled-item trace:

- **Target & labels:** (1) label volumes per goal and window — both goals (Page View, Purchase) ship per batch-02; volumes decide each goal's windows, not which goal goes first (§1.9); (2) which windows will be offered per goal (possibly advertiser-selectable, §1.9), confirming the 1-day variant the batch-02 report names, and whether the attribution method (click- vs. view-through) can be exposed at all; (3) real attribution coverage / handling of unmatched/privacy-limited conversions? (4) existing CVR baselines to calibrate against?
- **Data access & features:** (5) sanitized real bid-request samples for premium video/TV (current samples are banner)? (6) mechanism + cadence for the bidder account to consume client data — partially answered: batch-02 names the source tables (§1.9); the cross-account mechanism stays open, now owned by the DE lane; (7) achievable feature freshness per category — partially answered: the cadence tiers are published (§1.5); still open whether a fresher-than-hourly boundary feed is achievable; (8) Max CPA at bid time — **answered by batch-02**: the ad set's existing `max_bid`, read from ad set config and reinterpreted per `bidding_strategy` (CPA under goal_cpa, §1.9).
- **Serving & latency:** (9) expected/peak throughput and candidates-per-request distribution — team working numbers exist (1M req/s, 10 candidates/request, §2.7) pending client confirmation; (10) latency budget for the ML step within the 10ms envelope? (11) Go monolith or multi-service — internal (SW-team benchmark), not a client ask; kept for completeness; (12) GPU available, or CPU-only for MVP?
- **ML interface:** (13) probability vs. expected value — the client leaves it explicitly open (§1.9); our proposal is probability only (ADR-0001, contradiction #1), to present for their confirmation.
- **Tooling/infra/compliance:** (14)(15) training infra and registry — **settled: Databricks** (workloads, MLflow tracking, Unity Catalog registry; direct client knowledge); (16) reuse the client's MWAA or stand up our own — still open; (17) monitoring standard — ours to decide (Datadog lean), not a client blocker.
- **Lifecycle:** (18) retraining cadence and pre-serve validation — ours to decide after EDA, not a client blocker; (19) the goal-CPA evaluation window and fee treatment — the client's ML report marks both as remaining to be defined; we need them to compute the cost-per-action readouts (design_docs 06).

## 2.5 Dependencies & risks

- **Cross-account data access** — critical path; nothing trains/serves without it. Owned by the DE lane; the ML lane consumes the five curated datasets as a given.
- **Attribution definition** (windows per goal, volumes, method) — defines the prediction target; blocks the window choice per goal (label build itself is parametrized).
- **Real traffic samples** — needed to validate feature availability/latency on real video payloads (current fixtures are banner).
- **Compliance** (AI-use annex) — the annex constrains AI-system use for the work; tooling itself is settled (Databricks). Confirm annex scope against the signed contract.
- **Agent topology** (monolith vs. multi-service) — owned by the SW-team benchmark; the ML embedding choice is settled (pure library) and no longer depends on it.

## 2.6 ADR status

The `adr/` set uses MADR-lite (see `adr/template.md`, `adr/README.md`):

- **ADR-0000** — record architecture decisions (Accepted).
- **ADR-0001** — ML service returns calibrated `P(Action)`, not expected value (Accepted; amended 2026-10-15 — reaffirmed as our proposal to the client's now-explicitly-open interface question, with per-candidate response metadata and caller-side goal routing).
- **ADR-0002** — MVP serving = ONNX tabular GBDT on CPU, embedded/co-located in Go; Triton deferred (Accepted).
- **ADR-0003** — calibration mandatory, versioned with the model as a matched pair, baked into the served artifact (Accepted; amended 2026-10-15 — the calibration component may be parameterized: per-window variants and a future per-advertiser lookup with shrinkage, still in-artifact).
- **ADR-0004** — attribution window + method defining the training label (**Proposed, blocker**; reframed 2026-10-15 — goal × window model granularity as default, window possibly advertiser-facing config, up-calibration as conditional alternative; method still pending the client).
- **ADR-0005** — cross-boundary data-access / data-engineering ownership (**Proposed, blocker**; reassigned 2026-10-15 to the **Data Engineering lane** — ML treats the five curated datasets as a given and states requirements).
- **ADR-0006** — the served artifact is the self-contained pipeline (preproc → model → calibration in one ONNX graph) (Accepted).

## 2.7 Testing lane (Olena, 2026-10)

Team-authored testing docs under `docs/batch_02/md/testing/` — ours, not client-confirmed:

- **Test strategy (draft):** TypeScript monorepo (pnpm) with Playwright (component/integration, E2E, UI) + k6 (performance), Allure reporting, Prometheus + Grafana for performance runs. CI tiers: per-PR smoke, nightly regression, weekly performance runs on a dedicated production-representative environment. E2E uses a deterministic ad-server emulator; integration testing against the real ad server is owned by the ad-server vendor's integration team. Rollout validation (shadow, canary, blue/green, progressive) is shared TA/ML/SRE.
- **Performance targets captured there (team-stated, to confirm with client):** 1M bid requests/sec throughput; E2E p99 ≤ 10 ms; **ML prediction p99 ≤ 3 ms**; 10 candidates/request as the initial assumption. Method: 1 warm-up + 10 measured runs, p99 evaluated per run, never averaged across runs.
- **AI test harness (vision + ROI):** a Claude Code-based agentic layer on top of the test-automation solution (requirements analysis → test design → implementation → execution/triage), build phases H0–H8 with human approval gates throughout. ROI model v2.0 (draft): reference case breaks even ~8.4 months, ROI 100% ~16 months, sensitive mainly to triage volume. Effort estimates in `testing_estimate.md`.

---

## Team roster

*Per the task brief.*

| Name | Role | Focus |
|---|---|---|
| Rodrigo Cunha | Principal ML Engineer | Owner of the ML lane (this summary, discovery report, ADRs) |
| Matheus Bergmann | Senior ML Engineer | ML lane |
| Illia Slobozhanin | Principal Data Engineer | Data engineering |
| Augusto Pietroski | Senior SW Developer | Ingestor / pacing benchmarks |
| Yuri Mednis | Lead SW Developer | Software |
| Olena Ozerova | Principal QA | Quality |

---

## Artifacts (current)

| Artifact | Location | Contents |
|---|---|---|
| ML Lane Discovery Report | `reports/discovery_report/ML_Lane_Discovery_Report.md` | Discovery-level ML-lane plan, delivered 2026-09-22 and frozen: design areas A–H with leans, assumptions, client questions, risks. |
| This summary | `DISCOVERY_SUMMARY.md` | Consolidated client facts + our analysis (this file). |
| ADR set | `adr/` | ADR-0000 meta + 0001–0006 (status in §2.6); `README.md` (index), `template.md`. |
| Offline platform design | `design_docs/` | Design docs for the offline ML platform — the set is complete (00–09): overview, data access, datasets, labels, features, training, validation/promotion, deployment job, orchestration/repos, monitoring. |
| Client questions | `design_docs/CLIENT_QUESTIONS.md` | The top-priority questions for the client, self-contained and sendable. |
| ML serving lib | [github.com/cunha-sigma/ml_serving](https://github.com/cunha-sigma/ml_serving) | The MVP Go serving library (ONNX artifact + manifest, rollout config, hot-feature mirror, decision logs). Externalized repo; no local copy. |
| Serving benchmark | [github.com/cunha-sigma/ml_serving_bench](https://github.com/cunha-sigma/ml_serving_bench) | Frozen serving-latency benchmark (engines `leaves` + ONNX Runtime, stage-placement arrangements, serving report). Externalized repo; no local copy. |

*Client source docs live under `docs/batch_01/` (initial set: `Documents - UA/`, AI annex, tech-debt process; converted Markdown in `batch_01/md/`) and `docs/batch_02/` (2026-10: `client_reports/` + Olena's `testing/`; converted Markdown in `batch_02/md/`). The arch-diagram image is `batch_01/md/Documents - UA/_media/media/image1.png` (not machine-readable here).*

---

## Contradictions & gaps noticed

1. **ML output = probability (our proposal — see ADR-0001, amended):** the client docs' formulas have the Bid Decision service apply `× Max CPA`, but the client's own prose names the service in EV terms (scope-doc heading "ML Prediction Service (Expected Value formulation for Ad Ranking)"; the batch-02 report's "providing the expected-value input"), and batch-02 leaves probability-vs-EV explicitly open ("must at least provide the goal p(Action)"). ADR-0001 (probability only) is our answer to that open question, to present to the client.
2. **Serving-topology tension:** UA_Infra prescribes a **dedicated EKS (Kubernetes) cluster** for the bidder, while our ML lean is an **embedded/co-located Go** serving path (ONNX on CPU) to minimize hops, with Triton/GPU deferred. These are reconcilable (EKS can host a Go service): the ML side is settled as a pure Go library embedded in the agent (ml_serving; no server mode), validated by our serving benchmark ([ml_serving_bench](https://github.com/cunha-sigma/ml_serving_bench)) and recommended as the all-in-ONNX artifact embedded in Go (ADR-0006). What remains open is the agent's own runtime shape (monolith vs. multi-service — the SW-team benchmark question).
3. **Banner samples vs. premium-video product:** all provided fixtures/payloads are **banner** examples (from the DSP tool), explicitly not client production traffic; the product is **premium TV/video** (the `adset_type` enum currently includes video). We cannot validate feature availability or latency on representative payloads yet (the real-traffic-samples question, §2.4).
4. **AI-use annex (now in the doc set):** present at `docs/batch_01/md/AI annex for Comcast.md`. It restricts using AI systems not provided by the client's parent company for the work without written approval; it does **not** govern ordinary tooling choices (e.g., MLflow). Confirm its scope against the signed contract.
5. **Goal-priority drift across client docs:** the batch-01 scope doc framed **Purchase as likely top priority with Page View as the likely fallback**; the batch-02 ML report (§1.9) prioritizes **Page View and Purchase together** as the initial models. Both goals ship; label volumes decide each goal's windows, not which goal goes first.
6. **Empty tech-debt register:** process is defined but the register is a blank template — no logged items yet.

# Open questions — consolidated register

Every open question in the offline design, deduplicated and grouped by
who resolves it. Each per-doc list remains the local view; this file is
the merged one. `CLIENT_QUESTIONS.md` holds the client-facing subset,
phrased to send.

## Client — only the client can answer or decide

| Question | What it unblocks | Sources |
|---|---|---|
| Which attribution windows will be offered per goal (advertiser-selectable?); confirm the 1-day table; the goal → `event_name` mapping. Our first-stage contract proposal (2026-11, unconfirmed) puts a **static 14-day window for all advertisers** on the table, carried as `attribution_window_days` per ad-set record — client confirmation would settle the stage-1 window | model granularity per goal; the label build's goal filter | `PLAN.md` OQ1, `00_overview.md` OQ1, `03_labels.md` OQ1 |
| Can the attribution method (click- vs. view-through) be exposed per conversion? | label semantics and inspectability | `PLAN.md` OQ1, `03_labels.md` OQ2 |
| How to identify served impressions (filter or wins-only), the impression↔conversion join key, and which layer backs the attribution feed. Our first-stage contract proposal (2026-11, unconfirmed) requires the win-log stream to carry the auction ID from the bid request, explicitly for decision reconstruction and training labels — a proposed join key pending client confirmation | the label universe and the join the label build stands on | `PLAN.md` OQ5, `03_labels.md` OQ3 |
| The cross-account transfer mechanism (carried by the DE lane) | the read path and the hot-feature freshness floor | `PLAN.md` OQ3, `01_data_access.md` OQ1 |
| Do the five curated datasets ship as named; exact schemas against our stated requirements | raw/cleaned column lists; the identity-triplet check | `01_data_access.md` OQ2, `02_datasets.md` OQ1 |
| Privacy/PII review: field-by-field drop/hash/retain, hashing sufficiency, `gdpr_consent_string`, dev-data use | cleaned-layer rules; the dev environment's data | `PLAN.md` OQ4, `02_datasets.md` OQ3, `08_orchestration_repos.md` OQ2 |
| Committed cadence per shared dataset; is a fresher-than-hourly delivery feed an option? | training recency and the online-feature freshness floor | `01_data_access.md` OQ3, `04_features.md` OQ1 |
| The cost-per-action evaluation window and fee treatment (their own stated TBD) | aligned cost-per-action readouts | `06_validation_promotion.md` OQ2 |
| Does the ad server give the agent a real-time win-notice/price signal, or only the hourly curated feed | the spend and win-rate guardrails' actual latency floor | `06_validation_promotion.md` OQ5 |
| Candidates-per-request **maximum and distribution shape** (the client says the max is pending from the ad-server vendor). Delivered 2026-11-02: averages — 13.9 per auction with the ad server's probabilistic pacing removed, 1.3 with it retained — plus full volume figures (auction RPS avg ~444k, p99 ~693k, max ~1.92M; bids avg ~21k/s) | serving capacity sizing; A/B arm-size math | `CLIENT_QUESTIONS.md`; standing discovery ask |
| Observed baseline conversion rates per goal | training's absolute gate thresholds and rollout bake times | `06_validation_promotion.md` OQ1 |
| MWAA: reuse the client's instance or run our own | where DAG code deploys; dev's instance | `08_orchestration_repos.md` OQ1 |
| Bidder response dataset: required fields, cadence, consumers | the export job's shape (assembly already designed) | `01_data_access.md` OQ4, `09_monitoring.md` OQ4 |

## Ours — answered by EDA once data access lands

| Question | What it sets | Sources |
|---|---|---|
| Label volumes per (goal, window) | window choice per goal; downsampling policy; Platt-vs-isotonic threshold; tuning budget | `PLAN.md` OQ1, `03_labels.md` OQ1, `05_training.md` OQ1 |
| Advertiser-layer eligibility threshold and shrinkage strength | per-advertiser calibration activation | `05_training.md` OQ2 |
| Lookback and holdout lengths per goal | training-set build ranges | `05_training.md` OQ3 |
| Gate thresholds, bake times, minimum A/B arm sizes | rollout policy values | `06_validation_promotion.md` OQ1, OQ3 |
| Drift and degradation thresholds, minimum volumes | retraining triggers | `09_monitoring.md` OQ3 |
| Retention numbers (cleaned 13 months; decisions 3 months — both proposals) | storage commitments | `02_datasets.md` OQ2, `09_monitoring.md` OQ5 |
| Hot-store keyspace sizing (join-key cardinality vs. the whole-keyspace mirror) | whether any feature needs a non-mirrored path | `04_features.md` OQ3 |
| High-cardinality categorical encoding (vocabulary + out-of-vocabulary vs. hashing) | the in-graph encoder | `05_training.md` OQ4 |
| Maturity margin value; how attribution-reprocessing events are detected | label finality; backfill triggering | `03_labels.md` OQ4 |
| Freshness budget per feature (staleness each feature tolerates) | per-feature cadences and TTLs | `04_features.md` OQ1 |
| A/B cost and duration (depends on label maturity speed — hours vs. the full attribution window) | whether A/B stays reserved for high-risk experiments or becomes cheap enough to use more often | `06_validation_promotion.md` OQ6 |

## Ours — team decisions, no external dependency

| Question | Decided with | Sources |
|---|---|---|
| The decision-log sink the agent wires the logger to (assume S3) | the agent lane | `00_overview.md` OQ2, `09_monitoring.md` OQ1, `PLAN.md` OQ2 |
| Alert routing: the single pane for the bidder account | team + infra | `09_monitoring.md` OQ2 |
| Key-presence validation at deploy time: existence only or value distributions | team | `04_features.md` OQ2 |
| Which role holds the two approval gates | team | `06_validation_promotion.md` OQ4 |
| Repo hosting (client organization or ours) | team + client | `08_orchestration_repos.md` OQ3 |
| Dev/prod account topology (working assumption: same account) | team + infra | `08_orchestration_repos.md` OQ4 |

`PLAN.md` OQ6 is a rollup of `08_orchestration_repos.md`'s open
questions; its surviving items live in the client table (MWAA; dev
data under the privacy row) and the two rows above.

## Serving-side changes to schedule ([ml_serving](https://github.com/cunha-sigma/ml_serving))

The work list the design still requires from the serving lib; the
designs here already assume these shapes.

| Change | For |
|---|---|
| An S3 source for the rollout config (or an S3-to-file sync); the artifact S3 source exists | the deployment jobs write S3; the lib must read it |
| Per-candidate goal (and window), model name, and config revision in the scoring response — or close as satisfied by slot identity plus the decision record (each slot serves one goal; the revision rides the decision row) | the bid-decision step, decision reconstruction, and the response contents ADR-0001 states |
| Validate (or default) `challenger.sample_rate`: an absent or zero rate makes shadow silently score nothing, and the lib's config validation accepts it | safe shadow-stage config writes |
| Every model input in the decision row, hot-feature values included — today the lib logs the request and candidate input maps only | input-drift monitoring and train/serve skew checks on decision rows |
| Staged config propagation and alarm-rollback ownership | safe config rollout at fleet scale |
| Redis credential-rotation ownership: the lib gained auth/TLS options, rotation is an open serving-side question, and the candidate schemes are ops-only — ours to co-own as the store's writers | the hot-store write path |
| Doc alignment: the serving docs still describe `queued` as jobs-API self-trigger bookkeeping (consumption is now a plain config write by the readout pass) and still list offline replay as the adopted rollout's step 1 (replaced by the absolute training-time gate) | serving docs matching the agreed design |

Standing prerequisite, not a code ask: shadow scoring runs only on
pods built with the lib's shadow-sessions option (a process setting
the rollout config cannot enable), and those sessions are a permanent
core reservation — both feed the serving capacity sizing.

Shipped by the lib (verified 2026-11-18, commits through 2026-11-13):
the shadow scorer — bounded worker pool, attempted-versus-dropped
counters, queue-depth gauge, shadow rows to the decision logger under
the `shadow` arm; `Slot.LiveVersions` for fleet version coverage;
Redis auth and TLS options; decision rows carry request
id, model inputs, routing salt, routing-unit value, and per-candidate
defaulted fields; the scoring response is per-candidate (probability,
arm, model version, defaulted fields); the rollout config has
fleet-load/shadow/canary modes with A/B nested in the ramp and a
`queued` slot; metrics are dimensioned by model/arm/version; challenger
routing is wired (champion fallback on missing unit or unloaded
challenger); the artifact source reads S3; slot naming is documented
lib-side; the serving repo closed its approval-placement and
label-delay questions with the `06_validation_promotion.md` answers,
and closed schema review as ML-lane-owned (no external gate).

Excluded as settled (resolved during the design audits): Max CPA
availability at bid time, probability-versus-expected-value interface,
environments and the deployment jobs' per-environment instantiation,
approval-gate placement, CI tooling and wheel publishing (GitHub
Actions to start; a package index, CodeArtifact as the working
assumption), and the deployment queue race (closed by the S3
conditional-write scheme, `07_deployment_job.md`). Answered by the client (2026-11-02):
premium-video bid-request samples (anonymized joined firehose events
delivered — real video traffic with quartile activity events), and the
volume/average half of the candidates-per-request ask (figures in the
row above).

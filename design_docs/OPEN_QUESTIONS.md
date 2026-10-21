# Open questions — consolidated register

Every open question in the offline design, deduplicated and grouped by
who resolves it. Each per-doc list remains the local view; this file is
the merged one. `CLIENT_QUESTIONS.md` holds the client-facing subset,
phrased to send.

## Client — only the client can answer or decide

| Question | What it unblocks | Sources |
|---|---|---|
| Which attribution windows will be offered per goal (advertiser-selectable?); confirm the 1-day table; the goal → `event_name` mapping | model granularity per goal; the label build's goal filter | `PLAN.md` OQ1, `00_overview.md` OQ1, `03_labels.md` OQ1 |
| Can the attribution method (click- vs. view-through) be exposed per conversion? | label semantics and inspectability | `PLAN.md` OQ1, `03_labels.md` OQ2 |
| How to identify served impressions (filter or wins-only), the impression↔conversion join key, and which layer backs the attribution feed | the label universe and the join the label build stands on | `PLAN.md` OQ5, `03_labels.md` OQ3 |
| The cross-account transfer mechanism (carried by the DE lane) | the read path and the hot-feature freshness floor | `PLAN.md` OQ3, `01_data_access.md` OQ1 |
| Do the five curated datasets ship as named; exact schemas against our stated requirements | raw/cleaned column lists; the identity-triplet check | `01_data_access.md` OQ2, `02_datasets.md` OQ1 |
| Privacy/PII review: field-by-field drop/hash/retain, hashing sufficiency, `gdpr_consent_string`, dev-data use | cleaned-layer rules; the dev environment's data | `PLAN.md` OQ4, `02_datasets.md` OQ3, `08_orchestration_repos.md` OQ3 |
| Committed cadence per shared dataset; is a fresher-than-hourly delivery feed an option? | training recency and the online-feature freshness floor | `01_data_access.md` OQ3, `04_features.md` OQ1 |
| The cost-per-action evaluation window and fee treatment (their own stated TBD) | aligned cost-per-action readouts | `06_validation_promotion.md` OQ2 |
| Does the ad server give the agent a real-time win-notice/price signal, or only the hourly curated feed | the spend and win-rate guardrails' actual latency floor | `06_validation_promotion.md` OQ5 |
| Candidates-per-request distribution (median, average, p99, max); volume figures if available | serving capacity sizing; A/B arm-size math | `CLIENT_QUESTIONS.md`; standing discovery ask |
| Sanitized premium-video bid-request samples (current fixtures are banner) | feature availability at bid time on real traffic | standing discovery ask |
| Observed baseline conversion rates per goal | first-model plausibility checks in the offline gate | `06_validation_promotion.md` OQ1 |
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

## Ours — team decisions, no external dependency

| Question | Decided with | Sources |
|---|---|---|
| The decision-log sink the agent wires the logger to (assume S3) | the agent lane | `00_overview.md` OQ2, `09_monitoring.md` OQ1, `PLAN.md` OQ2 |
| Alert routing: the single pane for the bidder account | team + infra | `09_monitoring.md` OQ2 |
| Key-presence validation at deploy time: existence only or value distributions | team | `04_features.md` OQ2 |
| Which role holds the two approval gates | team | `06_validation_promotion.md` OQ4 |
| CI tooling; where versioned wheels publish | team (+ client environment) | `08_orchestration_repos.md` OQ2 |
| Repo hosting (client organization or ours) | team + client | `08_orchestration_repos.md` OQ4 |
| Dev/prod account topology (working assumption: same account) | team + infra | `08_orchestration_repos.md` OQ5 |

## Serving-side changes to schedule ([ml_serving](https://github.com/cunha-sigma/ml_serving))

The work list the design requires from the serving lib; the designs
here already assume these shapes.

| Change | For |
|---|---|
| Decision rows carry request id, model inputs, routing salt, routing-unit value, and a per-candidate scored-versus-default flag (the row in `00_overview.md`, touchpoint 4) | label joins, replay, sample-ratio checks, per-candidate defaulted rates |
| The scoring response carries per-candidate metadata: goal (and window) answered, model identity, scored-versus-default flag | the bid-decision step and decision reconstruction |
| Rollout-config conventions for the fleet-load, A/B, and rollout-canary states | the deployment job's advance writes |
| Per-arm/version dimensions on the lib's metrics; shadow sampling and drop counters | per-arm health reads; the shadow readout |
| S3 sources for the rollout config and artifacts (or an S3-to-file sync) | the deployment job writes S3; the lib must read it |
| Staged config propagation and alarm-rollback ownership | safe config rollout at fleet scale |
| The slot-naming convention documented lib-side (slots named by goal, later goal and window) | predictable config paths and model names |
| Outbound: `06_validation_promotion.md` answers the serving repo's open questions on approval placement and label-delay proxies — send back | closing their open list |

`PLAN.md` OQ6 is a rollup of `08_orchestration_repos.md`'s list; the
08-sourced rows above cover it.

Excluded as settled (resolved during the design audits): Max CPA
availability at bid time, probability-versus-expected-value interface,
environments and the deployment job's per-environment instantiation,
approval-gate placement.

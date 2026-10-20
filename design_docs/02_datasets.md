# 02 — Datasets

The storage layout on our side: what tables exist, where they live in
Unity Catalog, how they are named, and the two conventions `00_overview.md`
defers here (identity-space naming, privacy treatment). Exact inbound
column schemas are open until the client's dataset inventory arrives
(`01_data_access.md`); this doc fixes grains, keys, and rules, not
column lists.

## The layers

Each layer has one rule that defines it:

- Raw — Unity Catalog external tables reading the client's curated datasets in
  place; no copy, no transformation, the client's schema as shipped. Our rules
  do not apply here: the data is the client's, governed by their grants.
- Cleaned — the first Delta tables we materialize: typed, deduplicated,
  identity resolved (three ID spaces as separate columns), cost and
  spend units normalized (raw log values arrive in micros, reporting
  values in currency; the cleaned column states its unit), privacy
  rules applied. Reshaped the client content, nothing computed. Everything
  downstream of the client-origin data reads cleaned, never raw.
- Decisions — ingested serving events (the lib's decision-log rows),
  parallel to cleaned but with a different origin: our own serving
  side, not the client. Ingestion owned by `09_monitoring.md`.
- Derived — tables whose content we compute: the labels table
  (`03_labels.md`), the materialized feature tables (`04_features.md`),
  the per-arm readout tables and the monitoring tables
  (`09_monitoring.md`). Rewritable by partition until their inputs are
  final, unlike training snapshots.
- Training — point-in-time joins of derived labels, cleaned data, and
  feature values into model-ready training sets. Immutable snapshots,
  one per training run.

## Catalog and naming

One catalog per environment (`ml_dev`, `ml_prod`) is our working
assumption (`00_overview.md`), open until the account and MWAA
questions land. The schema and table names below are our working
proposal: the other docs use them as the working set, and they adjust
on review, not on anything external.

Unity Catalog schemas map to layers plus one for decision-log tables:

- `raw` — external tables, one per curated dataset:
  `raw.impressions`, `raw.attribution_labels`, `raw.performance_hourly`.
- `cleaned` — same table names, materialized and conformed:
  `cleaned.impressions`, `cleaned.attribution_labels`,
  `cleaned.performance_hourly`.
- `derived` — computed tables: `derived.labels` (`03_labels.md`); the
  materialized feature tables `derived.feature_<model>_*`, one per
  model and join-key grain (`04_features.md`); the per-arm readout
  tables `derived.readout_<model>`; and the monitoring tables
  `derived.model_metrics` (one row per model, metric, cut, and day) and
  `derived.data_quality` (one row per check, dataset, and day) —
  contents in `09_monitoring.md`.
- `decisions` — ingested decision-log tables, starting with
  `decisions.scored_candidates`. Populated by `09_monitoring.md`'s
  decision-ingest pipeline; the tables are defined here because they are
  dataset-layer objects like any other.
- `training` — one table per model, `training.<model_name>`,
  partitioned by `run_id`, which IS the MLflow run id of the training
  run that produced each row (one id, no mapping table). Partitioning is what makes the single
  table work: fetching one run's snapshot prunes to that run's files
  regardless of how many runs the table holds, and retention is a
  partition drop. Rows for a run are written once and never updated;
  Delta time travel is not the snapshot mechanism (vacuum erases
  history), the explicit `run_id` partition is.

Full name example: `ml_prod.cleaned.impressions`.

## Grain and keys per dataset

Grains and primary keys are settled by what each dataset is; columns
inside each row await the inventory.

- Impressions — one row per served impression. Two working assumptions
  to confirm with the client, tracked in `03_labels.md`'s open question 3: the
  dataset is wins-only, and it carries a key the attribution rows
  reference (their tables use `impression_id`; the client's delivery-log
  inventory documents `auction_id`/`request_id`). This is the training
  and label universe.
- Attribution labels — one row per attributed conversion. The cleaned
  table unions the client's per-window, per-family source tables with
  `source_family` and `window` columns; its key is (`conversion_id`,
  `source_family`, `window`), since the client guarantees `conversion_id`
  unique only within each source table. Carries the measurement-source
  keys (`enhanced_pixel_id` web, `app_tracker_id` app) and joins to
  impressions on `impression_id` (required in the attribution tables,
  nullable in the gold query layer; which layer backs the curated feed
  is open). The conversion rows' own `ad_id` column is nullable on the
  web-attribution provider side; that never affects the label join (identity comes from
  the impression row), but any rollup joining conversions directly to
  ads or campaigns loses the null-`ad_id` rows. `03_labels.md` tracks
  that loss as a data-quality metric.
- Performance hourly — one row per ad × hour. The client's sources
  scope it to pacing, reporting validation, spend reconciliation, and
  feature use, not labeling; we use it for reconciliation checks only,
  impression-level attribution is the label source. Its spend fields arrive in normalized
  currency while win-log costs arrive in micros; the cleaned layer's
  unit normalization is what makes the reconciliation comparable.
- Scored candidates — one row per candidate the serving lib scored.
  Joins served impressions and labels by (`request_id`,
  `candidate_id`); supports per-arm aggregation by model, version,
  arm, and revision.
- Labels (`derived.labels`) — one row per impression and label
  configuration; grain and columns in `03_labels.md`.
- Feature tables (`derived.feature_<model>_*`) — one row per join-key
  combination and time bucket; one table per model and join-key grain,
  features as columns, maintained incrementally by the materialization
  pipeline (`04_features.md`). A bucket is computed from cleaned
  partitions; when a cleaned partition is rewritten (late or corrected
  data), the buckets computed from it are recomputed. Nothing else
  reopens a bucket.

## Identity-space naming convention

The rule `00_overview.md` assigns here. Three ID spaces exist (client UUID,
DSP ID, raw-log ID); a bare id column is ambiguous and therefore
banned from our layers:

- In `cleaned` and `training`, every entity reference is a column
  triplet with explicit suffixes, named by the client entity: `adset_client_id`
  (UUID, string), `adset_dsp_id`, `adset_raw_id` (the client's adset is the
  downstream "line item"; using the DSP-space name as the entity
  name would defeat the convention). Same pattern for campaign,
  creative, account, ad. A bare column like `adset_id` or
  `line_item_id` must not exist in these layers. Serving-side field
  names are a different world: a bid request's `line_item_id` is a
  serving field in the DSP/raw space, not one of our columns, and
  key templates keep serving names (`04_features.md`).
- We never create or compute these ids. The client controls identity mapping
  (stated), and their dataset guidance says all three ids should ship
  as separate, clearly named fields; whether every curated dataset
  actually will is unconfirmed, so the operative rule is the check: the
  cleaned layer renames the columns to this convention, verifies all
  three arrive filled, and reports any gap to the client rather than filling it
  ourselves. Every table built from cleaned keeps the same column names
  unchanged.
- `raw` keeps the client's names untouched; the convention applies from
  cleaned onward.

## Privacy treatment

The rule `00_overview.md` assigns here. Applies at the raw → cleaned
boundary; raw is the client-governed, cleaned onward is ours. Proposal: the
final field-by-field list needs the schema inventory and the privacy
compliance review (`PLAN.md` open question 4).

- Drop at cleaned — all IP-type fields (`ip_address`, `ipv6_address`,
  `impression_ip_address`, `event_ip`), all tracking and integration
  URLs (`postback_url`, `impression_tracking_url`), `user_email`,
  `event_user_agent`. Nothing we plan needs them; dropping beats
  governing.
- Hash at cleaned — `user_id`, `ifa`/`idfa`, device ids, `hhid`,
  `ga_client_id`: deterministic salted hash, same salt across datasets
  so joins survive, original values never stored. `user_id` arrives
  non-null on the web attribution tables (the client marks it required in that
  model; the app tables do not carry it), so it reaches us whether or
  not we use it; no documented join needs it, hashing is containment.
- Retain as-is — the consent signals (`is_gdpr`, `is_gdpr_consented`,
  `gdpr_consent_string`, `us_privacy`, `dnt`, `lmt`). They exist to
  gate feature use and retention; hashing them would defeat their
  purpose. One of them needs its own review: `gdpr_consent_string` is a
  full TCF consent payload, and whether retaining it as-is is
  acceptable is a question for the privacy review, not settled here.
- No privacy-sensitive field, hashed or not, may appear in a
  `training` table unless a feature definition explicitly declares it
  (`04_features.md`); the training layer defaults to entity ids,
  features, and the label.

## Retention and backfill

- Raw — no retention policy of ours; the data stays where the client put it
  under the client's lifecycle.
- Cleaned — partitioned by event date. Retention proposal: 13 months
  (one year of seasonality plus margin), to be sized against real
  volumes before prod.
- Derived — labels and feature tables follow their inputs: rewritable
  until final, retained on the cleaned layer's horizon.
- Training — snapshots retained while their model version is alive in
  the registry plus the rollback horizon; after that, deletable, since
  any snapshot can be rebuilt from cleaned.
- Decisions — retention driven by replay and readout needs; sized in
  `09_monitoring.md`.

## Incremental vs. full rebuild

- Cleaned tables build incrementally by event-date partition, with
  idempotent partition overwrite: re-running a day replaces that day,
  so reruns and backfills are the same operation scoped to different
  partitions. No special backfill path.
- Attribution labels arrive late, so old partitions get rewritten.
  Label partitions are keyed by the impression's date, but a conversion
  arriving today can belong to an impression up to 30 days old (the
  longest window); writing today's arrivals therefore rewrites old
  partitions. For normal late arrivals, a partition stays rewritable
  until its date is older than 30 days plus the delivery margin; after
  that it is final in normal operation. A model using a shorter window
  sees its labels stabilize sooner (a 7-day label is stable after 7
  days plus the margin); the 30-day bound is the blanket rule for the
  shared tables, not the wait every model pays. One event sits outside
  this rule: the client's attribution reprocessing runs at their
  weekly/backfill tier and may correct conversions in otherwise-final
  partitions; it is handled as an explicit backfill event that triggers
  downstream rebuilds, not absorbed by the margin.
- Training tables never rebuild in place: a new training run writes a
  new snapshot under a new `run_id`. Fixing a bad snapshot means a new
  run, not a patch.

## Open questions

1. Exact inbound schemas, formats, and paths; carried from
   `01_data_access.md`, blocks finalizing raw/cleaned column lists.
2. Retention numbers (cleaned 13 months, decisions horizon) need real
   volume data before they are commitments.
3. The privacy compliance review, three parts: the final
   field-by-field drop/hash/retain list; whether deterministic hashing
   of user-level identifiers suffices (and whether the review
   constrains where hashed fields may flow); and whether retaining
   `gdpr_consent_string` as-is is acceptable.

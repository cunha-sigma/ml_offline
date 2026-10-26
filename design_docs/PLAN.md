# Offline design docs: plan

The design-doc set for the offline ML platform. This file is the map;
each doc below is written in its own iteration. High level only: scope
per doc plus the questions it must settle.

## The serving contract comes first

[`ml_serving`](https://github.com/cunha-sigma/ml_serving) fixes the
online/offline interface. The offline platform exists to produce what
that lib consumes, so every doc here designs toward one of these four
touchpoints:

1. Published artifact — immutable ONNX artifact + `manifest.json` per
   version, on S3 (the filename is manifest-declared via `onnx.file`).
   The ONNX graph contains preprocessing + model + calibration; one
   input tensor per raw field, named identically to the field; raw
   strings pass through. The manifest carries the input schema and the
   hot-feature join spec (join keys, `key_template`, default).
2. Rollout config — one small mutable JSON per model slot: champion
   (later challenger + routing), version, artifact URI, checksums,
   audit fields (`updated_at`, `updated_by`), and a monotonically
   increasing `revision` that triggers hot swap. Written by a deployment
   job; the lib never talks to MLflow/Databricks. Slots are named per
   goal (later per goal and window); the bidding agent groups
   candidates by goal and calls the lib per slot, so a new goal is a
   new slot, not an interface change.
3. Hot-feature store — Redis, keyed by the manifest's `key_template`,
   float values. Populated by batch Databricks jobs (MWAA-scheduled)
   running the same feature-definition code training uses. The lib
   mirrors the whole store on a 5–10 min cadence; windowing/aggregation
   logic is entirely ours.
4. Decision logs — one row per scored candidate, emitted through the
   lib's logger interface: model, version, arm, revision, request id,
   candidate id, probability, timestamp, the model inputs, the routing
   salt, the routing-unit value, and a scored-versus-default flag. We
   use them for evaluation, drift, and rollout readout — never as the
   label universe.

Anything that changes these shapes is a cross-repo decision, not an
offline-only one.

## Platform

Client-confirmed: AWS; the client's warehouse is S3 + Athena + Iceberg + Glue +
Lake Formation with Postgres as config source of truth; the client's data jobs
run on Glue + MWAA; Databricks for ML workloads. Directed (ours):
within Databricks, Delta/Unity Catalog/MLflow with the UC registry
(assumption 1 below) for storage, tracking, and registry; our own
MWAA instance for orchestration. Details and the AI-use annex
constraint live in `CLAUDE.md`. Code lands in two repos: one for DAGs,
one for workloads. These docs design both.

## Working assumptions (directed, hold until told different)

1. Databricks is the ML platform; where
   options exist within it, we pick the Databricks-native one.
   Concretely: Delta as the table format, Unity Catalog as the catalog
   and governance layer (not Iceberg + Glue), and MLflow with Unity
   Catalog as the model-registry backend (not the legacy workspace
   registry). Delta/UC/MLflow are layers of one stack, not alternatives
   to each other.
2. Hot features are computable in batch; no streaming component for now.
3. One team owns everything end to end (Go, ML, data engineering, QA);
   responsibilities are per person, not per organization. No
   cross-team ownership boundaries inside this design; the Data
   Engineering lane (assumption 4) is a per-person lane inside the
   team, not another organization.
4. The five curated datasets are a given. Who produces them — the client
   directly, or our team's Data Engineer curating from the client's internal
   tables — and the cross-account mechanism are the Data Engineering
   lane's scope. This platform states its requirements on the datasets
   (label-universe semantics, join key, fields, freshness) and designs
   against them; provenance and transfer are out of scope here.
5. Attribution mechanics are externally fixed: the client's pipeline owns
   attribution and we never recompute it. The client's data models document
   7/14/30-day window tables, and the client's ML report states a
   1-day variant is also available (to confirm with the client); the window
   may become advertiser-facing configuration, making it a product
   dimension rather than one canonical choice. Both initial goals (Page View, Purchase) ship models, each
   on a single window for now; the expected end state is one model per
   (goal, window), each trained on its own window's labels, with
   up-calibration from a shorter window kept as a conditional
   alternative. The attribution
   method (click- versus view-through) is different: the client's attribution
   tables do not record which method attributed a conversion, so there
   is nothing to choose between until the client exposes that information. The
   label build is parametrized over all of it, and late-maturing
   labels are handled as a first-class property.

## Doc set

Numbered by dependency, not priority. Each settles its own decisions and
lists what it leaves open.

`00_overview.md` — end-to-end system map: data flow from raw events to
the four touchpoints, components, responsibilities within the team,
environments.
Settles: the one diagram everything else refers to; what is in scope for
offline vs. the serving/agent side.

`01_data_access.md` — consuming the client's curated datasets (impression-level
training data, attribution labels, aggregate performance) plus our own
decision-log landing zone; how the curated data is produced is out of
scope.
Settles: the read path into Databricks (Unity Catalog external tables,
in place); our lean on Athena. Leaves open by design: the cross-account
mechanism and the exact schemas (client-side).

`02_datasets.md` — storage layout on our side: raw (external tables, in
place) → cleaned (first materialized Delta) → derived (our computed
tables, including the readout and monitoring tables) → training
(immutable snapshots), plus a decisions schema for
ingested serving events, under Unity Catalog; retention; backfill.
Settles: catalog/schema naming; schema per dataset; incremental vs. full
rebuild; the identity-space naming convention (three ID spaces as
separate fields); privacy drop/hash/retain rules.

`03_labels.md` — the training label: joining the client's impression-level
training dataset (assumed wins-only, to confirm) to the attribution
labels dataset, bridged by the impression key; label maturity handling.
Settles: join mechanics (orphan tracking; the nullable `ad_id` affects
rollups, not the label join); goal and window as parameters — both
initial goals (Page View, Purchase) get label configs, one per
(goal, window); which windows ship pends label volumes and the
offered-window set; how immature labels are excluded.

`04_features.md` — feature definitions as the single shared layer:
training joins and hot-store population call the same code (the no-skew
contract already proven at dev scale in
[ml_serving](https://github.com/cunha-sigma/ml_serving)); batch hot-feature
jobs.
Settles: repo home of the shared layer; feature materialization (the
offline half of the feature store: `derived.feature_<model>_*` tables per
join-key grain, maintained incrementally, versioned per definition,
with inline compute as the training-side fallback); the cadence
proposal for the 30 min windows (batch, per assumption 2; floored by
inbound data freshness); key-space and defaults per manifest.

`05_training.md` — the training-set build (point-in-time join of labels
and features, maturity cutoff, negative downsampling with recorded keep
fraction) plus training + calibration + ONNX export as Databricks
workloads; MLflow tracking; the export parity check as a hard gate.
Settles: pipeline structure (build → optional hyperparameter tuning →
fit → calibration → evaluation → export + parity → registration) with
four run modes (full train, tune and train, recalibrate-only,
window-variant export); model scope: one global model per goal,
on a single window each for now, expected to extend to one model per
(goal, window) once the client's offered windows firm up (up-calibration from
a shorter window stays the conditional alternative); advertisers enter
as model features, never as per-advertiser models (the client's
sparse-signal requirement), with stratified downsampling considered so
large advertisers do not drown small ones; calibration method per
model: one general calibrator for the MVP, with the design absorbing
future advertiser-wise calibration (the general calibrator plus
specific ones for the advertisers with enough data, fit with shrinkage
toward the general fit, baked into the same artifact); export
validation bar; label/feature config lineage with the model version.

`06_validation_promotion.md` — the decision logic of the Databricks
deployment job (one job, two docs with `07`): rollout policy, per-arm
readout, promotion/rollback verdicts, approval placement. Ranking and
calibration gates themselves live in `05_training.md`, before a
version ever registers.
Settles: thresholds, including per-advertiser calibration
error as a standard evaluation cut (it detects when a per-advertiser
calibration layer would earn its place); manual vs. automated gates;
proxy metrics while labels mature.

`07_deployment_job.md` — the deployment job itself, the bridge to
serving: triggered by model registration; task per step (claim,
export, advance, read out, promote/rollback); immutable artifact +
manifest on S3; rollout config writes with bumped revision; rollback =
config pointing at a previous version.
Settles: task structure and the execution model (one Lakeflow job, two
branches by trigger; registration starts a rollout, scheduled and
alert-triggered readout passes move it; per-task compute; the rollout
config's content is the state; approvals as model-version tags); the
write paths into shared state (same installation); the key-presence
validation handoff with `04_features.md`.

`08_orchestration_repos.md` — the two repos: the DAG repo holds the
pipeline framework and every per-pipeline definition (DAG file,
pipeline YAML pinning `package_version`, workload YAMLs = model config
and rollout policy); the workload repo is the pipeline-agnostic
versioned package (logic + config schemas) plus the one standing-job
bundle (the deployment job). Pipelines are submitted at trigger time
with the pinned wheel; schemas are owned by the workload package and
validated in the DAG repo's CI.
Settles: repo layouts and the definitions-vs-machinery split; the
submit-time invocation pattern with explicit version pinning; testing
strategy; environment mechanics (dev/prod catalogs, per-env config);
the deployment job as one definition instantiated per environment.

`09_monitoring.md` — offline monitoring and decision-log ingestion:
landing the rows, the datasets derived from them (per-arm readout
tables, the bidder response dataset the client wants back), pipeline alerting,
drift and calibration tracking, retraining triggers.
Settles: the decision-ingest pipeline (~30 min proposal) and the
readout-table build versus readout pass split; the monitoring DAG
(parametrized per model, daily) with `derived.model_metrics` and
`derived.data_quality` and the threshold-to-action mapping
(recalibrate-only, full train, alerts); data-quality check ownership
per producing pipeline; retraining triggers; the bidder response
dataset's assembly.

The doc set is complete: 00–09 written.

## Open questions (ask, do not assume)

1. Which attribution windows the client will offer per goal (the client's ML
   report suggests advertiser-selectable windows, and states a 1-day
   attribution variant exists — to confirm, since the client's data models
   document only 7/14/30-day tables), and label volumes per
   (goal, window) — both initial goals (Page View, Purchase) ship,
   so the volumes decide each goal's windows, not which goal goes
   first. Separately, the attribution method (click- versus
   view-through): the client's tables do not record it, so the question to the client
   is whether that information can be exposed at all.
2. Decision logs: which sink the Bidding Agent wires the lib's logger
   to. We assume the rows land on S3, somewhere we can read.
3. The cross-account transfer mechanism for the curated datasets (Lake
   Formation share, S3 export or replication, event stream, or API) —
   owned by the Data Engineering lane (working assumption 4); tracked
   here only because it fixes the read path and the freshness floor
   for hot features.
4. The privacy/PII compliance review: final field-by-field
   drop/hash/retain list (`02_datasets.md`), whether deterministic
   hashing suffices, and `gdpr_consent_string` retention.
5. The label universe and join key: whether the curated
   impression-level dataset is wins-only (derived from the win logs —
   every row a served impression) and which key it carries
   (`impression_id` vs `auction_id`/`request_id`); detailed in
   `03_labels.md`'s open question 3. Settled on our side: auction and
   bid data are never the label universe — `P(Action | Impression)`
   conditions on a served impression — they enter only as feature and
   analysis sources.
6. Orchestration-side opens, detailed in `08_orchestration_repos.md`:
   MWAA reuse versus our own instance; CI tooling and wheel publishing;
   repo hosting; dev-data policy; dev/prod account topology (same
   account is the working assumption).

Settled since first drafted (recorded in `00_overview.md`): everything
runs in one installation (Bidding Agent on K8s) and environments are
dev + prod, nothing more. Deferred, distinct from settled: which managed
AWS Redis service.

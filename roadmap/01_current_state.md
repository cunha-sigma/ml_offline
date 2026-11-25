# 01 — Current state (2026-11-19)

The baseline the phases in `03_phases.md` start from.

## Per repo

| Repo | State |
|---|---|
| `ml_offline` (this repo) | **Design complete.** design_docs 00–09 cover the whole platform; full 3-scan audit passed 2026-11-18; the 2026-11-13 workload-repo decisions are absorbed. Sample-level EDA done (dossier + deck on the client's anonymized firehose samples). |
| `ml_offline_repos_scaffold_design` | **Design complete, zero code.** ~1,000 lines specifying frodo and gandalf: per-stage single-task Databricks runs chained by Airflow, `frodo run <stage>` CLI, concern-per-file configs with pydantic schemas, wheels to a package index (CodeArtifact assumed), GitHub Actions calling make targets, the two deployment jobs in frodo's bundle, prod deploy on release tag. Review branch not yet merged to its main. |
| `gandalf` (DAG repo) | **Skeleton + tooling only** (created 2026-11-18). Dev tooling is done: uv, ruff, mypy, import-linter contracts, pre-commit, Makefile (setup/lint/test), DAG-parse test, docs/ADR process, Airflow 2.11.2 pins. Absent: every framework module (`shared/` is empty), every pipeline folder, all CI workflows. |
| `frodo` (workload repo) | **Does not exist.** Creation planned for the week of 2026-11-23. Everything — package, CLI, stages, schemas, tests, bundle files — is design-only. |
| `ml_serving` (serving lib) | **Furthest along — the cross-lane work list is fully delivered** (items 1–14 of the per-item record at its repo root, as of 2026-11-19): shadow scorer, challenger routing, full decision record **including joined hot-feature values**, shadow `sample_rate` validation, and `Options.ModelRoot` — the lib reads and polls artifacts *and* the rollout config from the model's S3 folder itself, so no config-sync component exists. Still open: hot-store credential rotation (joint design), staged propagation/alarm-rollback ownership, capacity sizing, hot-key TTL ownership; one confirmation owed back (the hot-feature replay split). Our record: `research/ml_serving_requirements.md`. |

## Absent everywhere

- **Infrastructure-as-code: none.** No Terraform/CDK/CloudFormation in
  any repo; no provisioning for S3, MWAA, Databricks workspace,
  CodeArtifact, Redis, IAM, or observability. The IaC approach itself
  is undecided.
- **CI/CD: none.** No workflow files in any repo; no package index
  exists; no bundle deploy; no DAG sync.
- **Data access: not landed.** The curated datasets are named but no
  transfer/share mechanism exists (DE lane). Dataset-scale EDA is
  blocked on it.

## External gates (full register: `design_docs/OPEN_QUESTIONS.md`)

| Gate | Blocks |
|---|---|
| Cross-account data-access mechanism (client + DE lane) | dataset-scale EDA; cleaned ETL; everything downstream of data |
| MWAA: reuse the client's instance or run our own | where DAGs deploy; part of infra provisioning |
| Dev/prod account topology | infra layout (low design impact, moves targets) |
| Attribution windows / join key / baseline CVRs (client) | label build config; EDA targets; rollout thresholds |
| Databricks vs. alternative stack (see `04_databricks_alternative.md`) | the shape of infra + deployment-job work; cheapest to decide before Phase 1 |

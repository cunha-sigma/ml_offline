# Roadmap — offline ML platform build

High-level build plan for everything the offline ML design requires:
infrastructure, EDA and model exploration, the two code repos
(framework + workloads + DAGs), the deployment jobs, auxiliary jobs
(monitoring, hot features, decision ingest), and the path to the first
live model. Planning visibility only — no per-task implementation
detail; each task's detail lives in the design docs it points to.

**Snapshot date: 2026-11-19.** Durations are rough ranges in
engineering weeks, assuming current team capacity; no owners are
assigned here. Re-baseline this folder when a phase completes or a
gate resolves.

## Files

| File | Contents |
|---|---|
| `01_current_state.md` | What exists today per repo, what is in flight, what is absent; the external gates |
| `02_workstreams.md` | The work breakdown: scope, key deliverables, and dependencies per workstream |
| `03_phases.md` | The phased plan: order, durations, dependency diagram, critical path |
| `04_databricks_alternative.md` | Relative-effort cost of building on an AWS-native stack instead of Databricks |

## Sources tracked

| Repo | Role |
|---|---|
| this repo (`ml_offline`) | the design (design_docs/ 00–09, ADRs, open questions) |
| `ml_serving` | the Go serving library (the four touchpoints' other side) |
| `ml_offline_repos_scaffold_design` | the written design for the two code repos below |
| `gandalf` | the DAG repo (Airflow framework + per-pipeline definitions) — started |
| `frodo` | the workload repo (versioned Python package + deployment-jobs bundle) — **not created yet** |

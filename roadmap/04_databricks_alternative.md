# 04 — Cost of the non-Databricks path

The design assumes Databricks (client-confirmed for ML workloads), but
if that assumption falls, the platform is rebuildable on AWS-native
services. This is a pre-study, high-level estimate of **relative
engineering effort** — no service has been evaluated in depth and no
dollar figures are implied. Confidence: low; a real study precedes any
decision.

## What changes, what doesn't

The design's load-bearing choices are stack-agnostic: Python offline /
Go serving with ONNX as the bridge, the four S3/Redis touchpoints,
Airflow chaining per-stage runs, the two-repo split, the two
deployment jobs. **None of that changes.** What changes is the
execution backend each piece runs on, and who operates the services
Databricks bundles.

## Per capability

| Databricks gives us | AWS-native replacement | What we build/operate instead | Effort impact |
|---|---|---|---|
| Spark compute (job runs) | EMR / EMR Serverless or Glue jobs | gandalf's stage operator swaps the Databricks submit for the EMR/Glue equivalent; frodo's Spark code is mostly intact | Low–moderate |
| Delta tables + Unity Catalog governance | Iceberg on S3 + Glue Catalog + Lake Formation | Table-format change in the data layers; permissions/governance rebuilt on Lake Formation (aligns with the client's own stack) | Moderate |
| MLflow tracking + model registry (managed) | Self-hosted MLflow (compute + database + S3) or the AWS ML platform's registry | The biggest hit: either we operate MLflow ourselves (a standing service with auth, backups, upgrades) or we port lineage/registry integration to a different API | High |
| Registration-triggered deployment job (Lakeflow attachment) | Registry events through EventBridge → the `deploy-register` job as a container task or Step Functions state | The trigger mechanics and the jobs' packaging rebuilt; the jobs' logic unchanged | Moderate |
| Asset Bundles (job definitions, per-env targets) | Terraform/Step Functions definitions for the standing jobs | More IaC surface, less convention | Low–moderate |
| Notebooks / dev experience | Managed notebook service or self-run JupyterHub | Dev-loop convenience work | Low |

## Summary

- **Platform-side workstreams roughly double**: infrastructure (A),
  frameworks (C), deployment jobs (E), CI/CD (G) absorb nearly all of
  the delta.
- **Model, feature, label, and DAG logic barely move** (<10%): the
  workloads are Python/Spark either way, and the DAG layer was built
  to swap its submit target.
- **A permanent operations tax appears**: every self-hosted replacement
  (MLflow above all) is a service we run forever, not a one-time build.
- Rough one-time add-on: **at least ~10 engineering weeks** on top of
  `03_phases.md`'s totals, concentrated in Phases 1 and 4, plus the
  ongoing ops burden — standing up and hardening the replacement
  services, the registry above all, does not compress.
- **Timing**: the decision is cheapest before Phase 1 (nothing is
  provisioned yet) and grows steadily more expensive after Phase 3,
  when table format, registry integration, and job triggers are live.

---
theme: default
title: "CI/CD for the ML Lane"
author: Rodrigo Cunha
transition: slide-left
paginate: true
---

<!--
FORMAT: one slide per `---`. Bullets/bold = ON-SCREEN content (low text).
HTML comments = SPEAKER NOTES, invisible to the audience. No
client/vendor names on-screen. Sources: design_docs 05/06/07/08/09,
the repos' scaffold design, ml_serving.
-->

# CI/CD for the ML Lane
## Repos · models · rollout

**Rodrigo Cunha** — Principal ML Engineer<br>
Custom Bidding Agent · ML Lane · 2026-11

<!--
- ~30s. The ML lane's CI/CD is fully planned, rollout included.
- Goal of this talk: show the whole chain, then draw the boundary
  with the Bidder Agent's own CI/CD (which is not settled yet).
-->

---

## CI/CD · Workload repo (pipeline logic)

<div class="h-15"></div>

```mermaid {scale: 1.0}
flowchart LR
  W1["PR"] --> W2["unit tests"] --> W3["wheel<br/>published"] --> W4["workloads run on fixtures<br/>(direct submit — no DAGs)"]
```

<div class="h-6"></div>

- Pure Python logic — unit-testable with **no infrastructure**
- Every PR publishes a dev wheel; a release tag publishes the real one
- The fixture runs go **straight to the compute platform**, fast and light

<!--
- Unit tests cover workload logic, config schemas, golden feature
  vectors, calibration math (closed-form expected outputs).
- Fixture runs: each workload submitted as a one-off run with the
  just-built wheel, small test fixtures, minutes not hours — proves
  install + execution on the real runtime, nothing about production
  data.
- Adoption flow: a new wheel changes nothing until a DAG-repo PR bumps
  that pipeline's package_version; that PR's CI validates configs
  against the new wheel's schemas, and the dev DAG runs after merge
  are the DAG-level integration test. No DAG is ever triggered by the
  workload repo's CI.
-->

---

## CI/CD · DAG repo (orchestration)

<div class="h-15"></div>

```mermaid {scale: 0.9}
flowchart LR
  D1["PR"] --> D2["unit tests · parse ·<br/>config checks"] --> D3["merge →<br/>sync to dev bucket"] --> D4["DAGs run<br/>in dev"] --> D5["release tag →<br/>sync to prod bucket"]
```

<div class="h-6"></div>

- Configs validated against the **pinned wheel's schemas** — before anything deploys
- Integration = the DAGs actually running on the dev environment
- **Prod is the same sync, gated by a release tag** — nothing reaches prod from a merge alone

<!--
- Parse must succeed without the workload package installed (the
  scheduler's constraint).
- Config validation is a CI-only import of the schema subpackage from
  the exact wheel version each pipeline pins.
-->

---

## CI/CD · ML serving lib (Go)

<div class="h-15"></div>

```mermaid {scale: 1.0}
flowchart LR
  S1["PR"] --> S2["unit tests"] --> S3["ships inside<br/>the agent"]
```

<div class="h-6"></div>

- A **library**, not a service — it deploys by being inside the Bidder Agent
- Its production proving ground is the **rollout process** (two slides ahead)

<!--
- The lib's own test suite runs on every PR as plain go test.
- The model's path (training gates, then rollout) is deliberately
  separate from repo CI/CD — next slides.
-->

---

## Per-repo CI/CD

<div class="h-10"></div>

| Repo | Every PR (CI) | Deploy (CD) | Integration |
|---|---|---|---|
| **Workload repo**<br>(pipeline logic) | lint + unit tests: workload logic, config schemas, golden feature vectors, calibration math | wheel to the package index (dev wheel per PR, release on tag) + deployment-jobs bundle | workloads run on fixtures — direct submit to the platform, no DAGs |
| **DAG repo**<br>(orchestration) | DAG parse test, unit tests, config validation against the pinned wheel's schemas | sync to the environment's DAG bucket (dev on merge, prod on tag) | run the DAGs on the dev environment |
| **ML serving lib**<br>(Go) | unit tests | ships inside the Bidder Agent as a library | the rollout process (two slides ahead) |

<!--
- Workload repo: pure Python logic — unit-testable without any
  infrastructure; golden vectors pin feature definitions; calibration
  math has closed-form expected outputs.
- DAG repo: parse must succeed without the workload package installed;
  configs are validated against the schemas of the exact wheel version
  each pipeline pins — a CI-only import.
- Serving lib: its smoke test scores a real exported artifact and
  compares against training outputs at 1e-4 — the same tolerance the
  training export gate uses, so the contract is tested from both sides.
-->

---

## The training pipeline is the model's test bench

<div class="h-12"></div>

```mermaid {scale: 0.75}
flowchart LR
  TR["train +<br/>calibrate"] --> EV{"evaluation gate<br/>ranking + calibration<br/>floors"}
  EV --> EX{"export gates<br/>ONNX parity 1e-4<br/>+ latency budget"}
  EX --> REG["register<br/>in the registry"]
  EV -. fail .-> STOP["version never exists<br/>downstream"]
  EX -. fail .-> STOP
```

<div class="h-4"></div>

- Model **performance is tested where the model is built** — every run, no exceptions
- A version that registers has already proven quality, exactness, and speed

<!--
- Evaluation: AUC/PR-AUC + calibration error against absolute floors,
  plus per-advertiser/campaign/time cuts.
- Export: the ONNX graph is scored against the Python pipeline on
  held-out rows (max diff ≤ 1e-4) and timed against the latency budget.
- Nothing downstream re-tests quality — the registry only ever holds
  versions that passed.
-->

---

## Rollout = deployment testing under production conditions

<div class="h-12"></div>

```mermaid {scale: 0.8}
flowchart LR
  FL["fleet load<br/>0% traffic"] --> SH["shadow<br/>scores real traffic,<br/>no bids affected"]
  SH --> CA["canary ramp<br/>live bids, guarded"]
  CA --> G{"approval"}
  G --> PR2["promote"]
  FL -. abort .-> RB["rollback<br/>automated"]
  SH -. abort .-> RB
  CA -. abort .-> RB
```

<div class="h-4"></div>

- Loading verified **fleet-wide at 0% traffic** · latency + score distributions on **real traffic before any bid**
- Guardrails with **automated abort** — always on · a **human approves** before champion

<!--
- This is where "integration testing" happens from the ML perspective:
  the artifact loads in the real serving fleet, scores real requests,
  and its behavior is measured before it influences a single bid.
- Every state transition is a config revision written by the
  deployment jobs; verdicts read pre-aggregated evidence tables.
- Abort is cheap: a config write pointing back at the previous
  version; the fleet picks it up on the next poll.
-->

---

## What's ours to test — and what isn't

<div class="h-18"></div>

<div class="grid grid-cols-2 gap-6">

<div class="border border-gray-400 rounded-lg p-4">
  <div class="font-bold mb-2">ML lane tests</div>
  <div class="text-sm">workload logic · orchestration ·<br>model quality (training gates) ·<br>artifact loading, parity, latency ·<br>rollout safety on the live fleet</div>
</div>

<div class="border-2 border-amber-600 rounded-lg p-4">
  <div class="font-bold mb-2">Bidder Agent CI/CD tests <span class="opacity-60">(TBD)</span></div>
  <div class="text-sm">the agent embedding the lib:<br>its build & container package the lib's<br>native runtime correctly · request<br>plumbing · timeout & fallback behavior ·<br>its own deploy</div>
</div>

</div>

<div class="h-4"></div>

<div class="text-center text-xl">

**no Bidder Agent container appears in any ML pipeline — the lib is the contract**

</div>

<!--
- The question "do we need a Bidder Agent container for integration
  tests?" comes from the agent's CI/CD being unplanned — the need is
  real, the location isn't our pipelines.
- Model loading split, likely Q&A: WE test that the lib loads and
  scores models (lib tests + fleet load at rollout). THEY test that
  the agent they build still lets the lib do it — their container must
  package the lib's native runtime, right architecture, process
  options, memory. Our tests prove the lib; nothing we run proves
  their image. Different failure modes, same contract.
- The lib ships with its own test fixtures (real artifact + expected
  scores), so the agent's CI can verify "loads and scores correctly"
  without any ML infrastructure.
- Both sides test the same contract: the lib's smoke test from inside,
  the agent's integration test from outside.
-->

---

## DAG deploys: the shared module, and changing code mid-run

<div class="h-10"></div>

- The DAG repo ships a **shared framework module** to the DAG bucket — imported by every DAG
- CD runs **per pipeline type**, or **for the shared module**
- Deploying mid-run is **safe when the DAG's shape doesn't change** — bug fixes and behavior tweaks inside existing steps; Airflow picks the new code up per task
- Changes to the **shape** — tasks added/removed/renamed, dependencies rewired, shared-module interfaces — get a **pause or a between-runs window**

<!--
- Airflow re-reads DAG code per task execution: a mid-run deploy never
  crashes the scheduler, but one run spanning a deploy can execute
  early tasks on old framework code and later tasks on new.
- Our design minimizes the exposed surface: stage logic lives in the
  wheel, pinned per run at submit time — only the thin chaining code
  and the shared module are swapped live.
- So the blanket pause-everything habit isn't needed for routine
  deploys; reserve it for structural changes, where in-flight runs can
  be orphaned.
- This shared-module CD detail is newer than the design docs — to be
  folded into the DAG repo's own docs as it's built.
-->

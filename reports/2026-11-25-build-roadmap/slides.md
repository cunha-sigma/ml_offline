---
theme: default
title: "ML Lane Roadmap — ML Platform"
author: Rodrigo Cunha
transition: slide-left
paginate: true
---

<!--
FORMAT: one slide per `---`. Bullets/bold = ON-SCREEN content (low text).
HTML comments = SPEAKER NOTES (Slidev presenter notes), invisible to the
audience. No client/vendor names on-screen. Source of truth: roadmap/
(01_current_state, 02_workstreams, 03_phases, 04_databricks_alternative),
snapshot 2026-11-19.
-->

# ML Lane Roadmap
## ML platform — from design to first live model

**Rodrigo Cunha** — Principal ML Engineer<br>
Custom Bidding Agent · ML Lane · 2026-11

<!--
- ~30s. Design phase is done; this is the plan to BUILD it.
- Full detail lives in the repo's roadmap/ folder — this is the summary.
- Durations are rough planning ranges, not commitments.
-->

---

## Where we are today

<div class="h-4"></div>

<div class="grid grid-cols-3 gap-4">

<div class="border border-gray-400 rounded-lg p-4">
  <div class="font-bold">Design</div>
  <div class="text-3xl mt-2">✅</div>
  <div class="text-sm mt-2">platform design 00–09, audited<br>+ the two code repos fully specified</div>
</div>

<div class="border border-gray-400 rounded-lg p-4">
  <div class="font-bold">Serving library</div>
  <div class="text-3xl mt-2">✅</div>
  <div class="text-sm mt-2">cross-lane work list delivered<br>scores, shadow, rollout config, decision logs</div>
</div>

<div class="border border-gray-400 rounded-lg p-4">
  <div class="font-bold">DAG repo</div>
  <div class="text-3xl mt-2">🟡</div>
  <div class="text-sm mt-2">skeleton + dev tooling exist<br>no framework, no pipelines yet</div>
</div>

<div class="border border-gray-400 rounded-lg p-4">
  <div class="font-bold">Workload repo</div>
  <div class="text-3xl mt-2">⬜</div>
  <div class="text-sm mt-2">not created yet<br>everything is design-only</div>
</div>

<div class="border border-gray-400 rounded-lg p-4">
  <div class="font-bold">Infrastructure</div>
  <div class="text-3xl mt-2">❌</div>
  <div class="text-sm mt-2">no provisioning code anywhere<br>no CI/CD in any repo</div>
</div>

<div class="border border-gray-400 rounded-lg p-4">
  <div class="font-bold">Data access</div>
  <div class="text-3xl mt-2">⏳</div>
  <div class="text-sm mt-2">datasets named, mechanism open<br>blocks EDA at scale</div>
</div>

</div>

<!--
- Design: ml_offline design_docs complete + the frodo/gandalf scaffold
  design, reviewed and decision-dated.
- Serving: ml_serving shipped all 14 agreed items — incl. shadow scorer,
  full decision record with hot values, and reading config straight
  from S3 (no sync component needed).
- gandalf: created last week — lint/test/tooling, zero logic.
- frodo: repo creation imminent.
- Infra: no Terraform/CDK anywhere; IaC approach itself undecided.
- Data access: the DE-lane/client question; the single biggest external
  dependency.
-->

---

## What the roadmap will build

```mermaid {scale: 0.8}
flowchart LR
  INF["Infrastructure<br/>(from zero)"] --> FRM["Frameworks<br/>DAG repo + workload repo"]
  FRM --> WKL["Workloads<br/>ETL · labels · features ·<br/>training · ingest · monitoring"]
  WKL --> DAGS["Pipelines<br/>one DAG per pipeline"]
  WKL --> DEP["Deployment jobs<br/>register · readout"]
  DAGS --> LAUNCH["First live model"]
  DEP --> LAUNCH
  SRV["Serving library<br/>(already built)"] --> LAUNCH
  EDA["EDA & model exploration"] -. thresholds, volumes,<br/>policy values .-> WKL
  CI["CI/CD + publishing"] --> FRM
  style SRV fill:#16A34A,color:#fff
```

<div class="h-2"></div>

- Green is **done**; the rest is ahead of us
- **EDA will run in parallel** — its outputs are config values, not code
- The serving side is already built — considering we can keep using ONNX

<!--
- Ten workstreams in roadmap/02; this is the dependency skeleton.
- Infra feeds everything; frameworks before workloads before DAGs.
- EDA is the parallel track: label volumes, baseline conversion rates,
  gate thresholds, bake times — all deferred to EDA by design.
- Deployment jobs: the two standing jobs writing artifacts + rollout
  config; serving reads both straight from S3.
-->

---

## Six phases

```mermaid {scale: 0.75}
flowchart LR
  P0["<b>0 · Gates & repos</b><br/>1–2 wk"] --> P1["<b>1 · Foundations</b><br/>infra · frameworks · CI<br/>3–5 wk"]
  P1 --> P2["<b>2 · Data backbone</b><br/>ETL · labels<br/>3–5 wk"]
  P2 --> P3["<b>3 · Features & training</b><br/>to a registered model<br/>4–6 wk"]
  P3 --> P4["<b>4 · Deploy & monitor</b><br/>rollout machinery<br/>3–5 wk"]
  P4 --> P5["<b>5 · E2E & launch</b><br/>3–4 wk + calendar"]
  ACCESS(["data access lands"]) -.-> EDA2["EDA track<br/>(parallel)"]
  EDA2 -.-> P3
  EDA2 -.-> P4
```

<div class="h-2"></div>

<div class="text-center text-xl">

**≈ 17–27 engineering weeks** · plus launch calendar time

</div>

<!--
- Phase 0 is mostly external: client answers + repo creation + the
  IaC and stack decisions.
- Each phase has an exit proof (next slide).
- The ranges assume current team capacity and the parallelism drawn.
- EDA starts the moment access lands, whenever that is.
-->

---

## Each phase proves something

<div class="h-4"></div>

| Phase | Exit proof |
|---|---|
| **1 · Foundations** | one trivial stage runs end to end: DAG → submitted run → pinned wheel |
| **2 · Data backbone** | labels table populated, reconciling against the source rollups |
| **3 · Features & training** | a registered, parity-checked model from real data, hot features live |
| **4 · Deploy & monitor** | a version flows fleet load → shadow in dev, readout tables filling |
| **5 · E2E & launch** | first champion serving; shadow → canary on live traffic |

<!--
- Not milestones for reporting — each proof de-risks the next phase.
- Phase 1's proof sounds small but it validates the whole execution
  model: Airflow chaining single-task runs on a versioned wheel.
- Phase 4's proof exercises the rollout machinery without touching
  live bids.
-->

---

## The critical path

```mermaid {scale: 0.9}
flowchart LR
  subgraph EXT["external"]
    DA["data access"]
  end
  DA --> E["EDA"] --> TH["thresholds &<br/>policy values"] --> L["launch"]
  INF2["infra"] --> F2["frameworks"] --> W2["workloads"] --> D2["DAGs"] --> L
  style DA fill:#D97706,color:#fff
```

<div class="h-2"></div>

<div class="text-center text-xl">

the highest-leverage action now: **land data access**

</div>

<!--
- Two chains: the external one (data access → EDA → the values every
  gate and policy needs) and the internal one (infra → … → DAGs).
- The internal chain is ours to pace; the external one is not — hence
  the ask. Everything EDA-gated can be built with placeholder values,
  but launch criteria need the real ones.
-->

---

## Plan B: losing the managed ML platform

**The scenario: we must build on raw cloud services instead.** What that does to the plan:

<div class="h-2"></div>

<div class="grid grid-cols-2 gap-6">

<div class="border border-gray-400 rounded-lg p-4">
  <div class="font-bold mb-2">Survives unchanged</div>
  <div class="text-sm">the design itself · Python↔Go split ·<br>ONNX artifact · S3/Redis contracts ·<br>Airflow chaining · the two repos ·<br>model / feature / DAG code</div>
</div>

<div class="border border-amber-600 rounded-lg p-4">
  <div class="font-bold mb-2">We build & operate ourselves</div>
  <div class="text-sm">Spark compute · table governance ·<br>experiment tracking + model registry ·<br>job triggers & bundles ·<br>notebook environment (EDA & exploration)<br><b>→ this is where the added work lives</b></div>
</div>

</div>

<div class="h-4"></div>

<div class="text-center text-xl">

**+10 weeks minimum**, one-time · **+ a permanent ops tax** · cheapest to decide **before Phase 1**

</div>

<!--
- Pre-study numbers, low confidence — a real evaluation precedes any
  decision.
- The biggest single hit is the registry/tracking service: either we
  operate it ourselves forever, or we port the integration.
- The design was built stack-agnostic on purpose; the cost is in who
  operates what, not in rework of the ML design.
-->

---

## What we need now

<div class="h-4"></div>

<div class="grid grid-cols-2 gap-6">

<div class="border-2 border-amber-600 rounded-lg p-4">
  <div class="font-bold">1 · Data access</div>
  <div class="text-sm mt-2">the transfer mechanism for the curated datasets — heads the critical path</div>
</div>

<div class="border border-gray-400 rounded-lg p-4">
  <div class="font-bold">2 · Platform decisions</div>
  <div class="text-sm mt-2">managed stack or not (Databricks?) · account topology</div>
</div>

<div class="border border-gray-400 rounded-lg p-4">
  <div class="font-bold">3 · Start the foundations</div>
  <div class="text-sm mt-2">both our repos (workload + DAG) · CI from zero · infrastructure — design is ready, but the stack decision (2) shapes this work</div>
</div>

<div class="border-2 border-amber-600 rounded-lg p-4">
  <div class="font-bold">4 · ONNX Runtime watch</div>
  <div class="text-sm mt-2">the inference engine's repo went private (security investigation) — settle our contingency; could change the serving lib a lot</div>
</div>

</div>

<!--
- 1 is the ask to push hardest — everything EDA-gated waits on it,
  and once data lands we compute baseline conversion rates ourselves.
- 2: only the genuinely open ones. Settled, not repeated here:
  orchestrator is Airflow; a package index will be used (not blocking);
  repo hosting is the client's enterprise GitHub.
- 3: Phase 1 in full — create the workload repo, build the DAG repo's
  framework (today it's a skeleton), stand up CI (none exists in any
  repo) and the dev infrastructure.
- 4: Microsoft took the ONNX Runtime repo private (malicious-content
  investigation, 2026-11). Our serving artifact executes on it. State
  today: all 1.30.0 artifacts archived locally with checksums,
  cross-verified against a second official channel; fresh image builds
  are broken (pull from the gone GitHub release) until we mirror.
  Contingency ladder: vendored source build (MIT, zero design change)
  is primary; alternate engine (Tract) is the only tested-able
  fallback pending an op-coverage check; single-file artifact is
  non-negotiable, so the pure-Go scorer path is ruled out. Watch for
  the investigation outcome before any version bump.
-->

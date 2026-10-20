# CLAUDE.md — design_docs (the client ML lane, offline side)

Design work for the **offline ML platform** behind the client custom bidding
agent's ML Prediction service: everything that happens outside the hot
path — ETL, label building, training, calibration, validation, hot-feature
aggregation, and publishing artifacts the serving side
([`ml_serving`](https://github.com/cunha-sigma/ml_serving)) consumes.

**Phase: design docs only. No implementations in this folder.** Plans
and design documents live here; code comes later, in its own repos (see
below). Implementations cited as proof (the shared feature function, the
parity gate) live in the serving repo, not here.

## Client-confirmed facts

- Cloud is **AWS**. The client's own warehouse stack: S3, Athena, Apache
  Iceberg, Glue Catalog, Lake Formation, with **Postgres** as the source
  of truth for config and entity state.
- The client's data jobs run on **Glue + MWAA/Airflow**, owned by the client's data-jobs
  team.
- **Databricks runs ML workloads.** Within it, compute, experiment
  **tracking**, and the **model registry** (MLflow with Unity Catalog),
  and Delta as table format are **our directed picks**, not
  client-mandated — building from scratch, we use Databricks-native
  functionality rather than reinventing it.
- An **AI-use annex** (Sigma-issued, contractual — not a client
  statement) prohibits using AI systems not provided by the client's
  parent company for the work without prior written approval, and
  obliges disclosure of AI systems in use.
- **Batch-02 ML Service Background (2026-10-11):** ad sets will gain
  `bidding_strategy` (`max_cpm` / `goal_cpa` / `lowest_cost`) and
  `optimization_goal` (`impressions` needs no model; `PIXEL_PAGE_VIEW`
  and `PIXEL_PURCHASE` are **both** initial model priorities; app
  events later). The ML service must return at least `P(Action)`; the
  probability-versus-EV interface is left open by the client (our
  proposal: probability only). The attribution window may
  become advertiser-facing configuration. Sparse-signal and new
  advertisers must be supported without per-advertiser models.

## Directed working assumptions (not client-confirmed)

- Our own **Airflow (MWAA)** instance for orchestration; whether we
  reuse the client's or stand up our own is an open client question.
- **A dedicated EKS cluster for the bidder**, most likely in its own
  AWS account — the client's infra doc recommends this, but a
  competing doc frames the bidder as a Terraform-ownership boundary
  inside shared infra instead; not settled.
- **The five curated datasets are a given.** Who produces them (the client, or
  our team's Data Engineer curating from the client's internal tables) and the
  cross-account mechanism are the Data Engineering lane's scope, not
  this platform's. We state requirements on the datasets; we do not
  design their provenance.

The remaining directed assumptions (batch-only hot features, single-team
ownership, input data reachable from our account, attribution handling)
are recorded in `PLAN.md`, which maps the whole design-doc set.

## Planned repo split

Two dedicated repos, separate from the serving lib
(`08_orchestration_repos.md` owns the design):

1. **DAG repo** — the pipeline framework plus **all per-model
   definitions**: one folder per pipeline with its DAG file, pipeline
   YAML (schedule, compute tier, `package_version`), model
   configuration, and rollout policy.
2. **Workload repo** — the pipeline-agnostic versioned Python package
   (training, calibration, ETL, feature logic, config schemas) plus the
   single standing-job bundle (the deployment job). Nothing
   model-specific lives here.

Pipelines are submitted at trigger time with the pinned package
version; no standing pipeline jobs exist. `design_docs/` itself is the
planning space for both; it does not become either repo.

## Boundary with serving

[`ml_serving`](https://github.com/cunha-sigma/ml_serving) is the Go
serving library. The contract between the two sides is four touchpoints
(detailed in `00_overview.md`): the **published artifact** (all-in-ONNX
model + manifest, immutable on S3), the **rollout config** (mutable,
revision-bumped, also on S3 — the lib never reads the registry), the
**hot-feature store** (we compute rolling-window aggregates into Redis;
serving only reads them), and the **decision logs** (serving emits, we
ingest). Offline owns everything up to the first three and everything
after the fourth. The shared feature-definition layer (one definition of
each hot feature used by both training joins and store population, to
prevent train/serve skew) is an offline deliverable.

## Conventions

- Write docs in team voice ("we/our"), direct and non-verbose.
- Python for all offline code (type hints on signatures) — when we get to
  code at all.
- **No references to files outside this folder.** `design_docs/` becomes
  its own standalone repo; a doc here must not point at `../` anything.
  State a needed fact directly instead of citing where it came from.
  External repos (`ml_serving`, `ml_serving_bench`) are the one
  exception and are always linked by their GitHub URL, never by a local
  path.

## No assumptions

When something is unclear, underspecified, or decidable more than one way,
**ask — do not assume**. This applies to requirements, scope, naming,
platform details, repo boundaries, and anything client-side we have not
confirmed.

- Never fill a gap with a plausible default and move on. Stop and ask.
- Never present an assumption as a fact in a doc. If we must write before
  the answer arrives, mark it explicitly as an open question or an
  assumption awaiting confirmation, and list who can answer it.
- A wrong guess in a design doc propagates; a question costs one message.

## Writing style (all docs in this folder)

Tone: objective, minimalist, complete. Every sentence either states a fact,
a decision, or a tradeoff; if it does none of those, delete it.

Banned LLM smells:

- No praise or hedging filler: "it's worth noting", "importantly",
  "robust", "seamless", "leverage", "delve", "crucial", "comprehensive".
- No summary paragraphs restating what the doc just said; no "In
  conclusion" / "Overall".
- No bullet lists where every item is `**Bold label:** sentence.` — use
  plain bullets or prose.
- No em-dash chains as a tic; at most one per paragraph, and only when a
  comma or period would not do.
- No rule-of-three padding ("fast, scalable, and reliable") — name the one
  property that matters.
- No rhetorical questions, no "Let's", no addressing the reader as "you".
- No vague quantifiers ("significantly", "various", "a number of") — give
  the number or drop the claim.

Structure:

- Say it once, in the one section where it belongs; cross-reference instead
  of repeating.
- Short declarative sentences. Active voice. Present tense for design,
  future tense only for actual schedule.
- Prefer a table or a diagram over prose when the content is enumerable.
- Headings name content ("Label join", not "Deep dive into labels").
- Completeness over brevity when they conflict: cover every case (failure
  paths, boundaries, ownership) in the fewest words that still decide it.
  Open questions are listed as open, not papered over.

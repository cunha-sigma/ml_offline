# ADR-0004: Attribution window and method that defines the training label

**Status:** Proposed (blocker — needs client input) · **Date:** 2026-09-22 · **Amended:** 2026-10-15 (batch-02 ML Service Background) · **Deciders:** Rodrigo Cunha (ML lane); pending client

**Context.** The label for `P(Goal Action)` comes from attribution: a positive is a served impression matched to an attributed conversion within a window; a negative has none. The batch-01 data models document **7/14/30-day** window tables for the web-attribution provider (web) and MMP (in-app); the batch-02 ML report states a **1-day** variant is also available ("one/fourteen/thirty day are available", plus its `PIXEL_PURCHASE_1_day` example) — the 1-day table needs confirming with the client. Labels mature late, so recent impressions are under-labeled. The batch-02 ML report changed the shape of the question: the goals are enumerated (`PIXEL_PAGE_VIEW` and `PIXEL_PURCHASE` both initial; app events later), and the **window may become advertiser-facing configuration** — a goal-suffixed value (`PIXEL_PURCHASE_7_day`) or a separate ad set column. If so, the window is a product dimension, not a single canonical choice. The client also asks the modeling question directly: separate models per window, or train on a short window and up-calibrate?

**Decision.** **Pending client input.** Working lean, replacing the earlier single-canonical-window lean:
- **Goal × window model granularity** as the expected end state: one model per (goal, window), each trained on its own window's labels. For now each goal ships on a single window, so slots are named per goal; when windows multiply, the routing key and slot naming extend to (goal, window) ([ADR-0001](0001-ml-service-returns-probability.md)).
- **Up-calibration** (train on the shortest window, fit a per-window calibrator on matured long-window labels) stays on the table as the client-suggested alternative, not the default — their question is framed on the 1-day window ("train off a 1-day view through and then up-calibrate?"), which presupposes the 1-day table. Its legitimate triggers are bootstrap history poverty (maturity eating the training range early in the system's life) and freshness; its validity gate is a ranking-invariance experiment — the long-window conversion rate must be a stable monotone function of the short-window score across segments. Mechanism in [ADR-0003](0003-calibration-matched-pair-artifact.md).
- **Method** (click- vs. view-through) unchanged: the client's window tables record no method; nothing to choose until the client exposes it.

**Why.** Open axes: which windows the client will actually offer per goal (now a product question, not just ours); label volumes per (goal, window); whether per-window rankings differ enough to require separate trees (likely goal-dependent — fast goals like page views may up-calibrate safely, laggy purchases likely not).

**Consequences.**
- The question to the client sharpens: which windows will be offered per goal, and label volumes per (goal, window) — top client-meeting priority.
- The label build stays parametrized over (goal, window); nothing blocks on the modeling choice itself.
- Drives training-window design, late/under-labeled handling, and calibration ground truth per window.

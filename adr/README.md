# the client — Architecture Decision Records

Decision record for the **client custom-bidding-agent**, with an **ML-lane focus** (the `P(Goal Action | Impression)` service and its offline pipeline). This folder holds only **critical, load-bearing decisions** — not every step. Add an ADR when a choice would be expensive to reverse or is needed to keep future work coherent.

- Format: MADR-lite (see `template.md`).
- One decision per file: `NNNN-short-title.md`.
- Status values: `Proposed` · `Accepted` · `Superseded` · `Withdrawn`.
- **Add ADRs by agreement** — propose the decision first, write the ADR once approved.

**Style — keep them atomic.** An ADR records one decision, tightly:

- Target ~15 lines. Context in 1–3 sentences, Decision in 1–2, the rest as terse bullets.
- State facts and the choice. No restating the problem across sections, no hedging, no prose that could live in a working doc.
- Capture *what* was decided and the load-bearing *why*; push narrative, exploration, and background to `DISCOVERY_SUMMARY.md` / `scratchpad.md` (delivered reports under `reports/` are frozen and never receive updates).

## Index

| ID | Decision | Status |
|---|---|---|
| [ADR-0000](0000-record-architecture-decisions.md) | Record architecture decisions for this project | Accepted |
| [ADR-0001](0001-ml-service-returns-probability.md) | ML service returns calibrated P(Action), not expected value | Accepted |
| [ADR-0002](0002-mvp-onnx-tabular-cpu-serving.md) | MVP serving is ONNX tabular GBDT on CPU; Triton/GPU deferred | Accepted |
| [ADR-0003](0003-calibration-matched-pair-artifact.md) | Calibration is a versioned matched-pair artifact baked into the served model | Accepted |
| [ADR-0004](0004-attribution-label-definition.md) | Attribution window and method that defines the training label | Proposed (blocker) |
| [ADR-0005](0005-cross-boundary-data-access.md) | Cross-boundary data-access pattern (curated exports vs. direct Athena) | Proposed (blocker, DE lane) |
| [ADR-0006](0006-served-artifact-self-contained-pipeline.md) | Ship preprocessing, model, and calibration as one ONNX file | Accepted (discovery — revisable) |

Accepted ADRs are our working decisions during discovery and may be revised on client input. `Proposed (blocker)` items need client answers before work can proceed.

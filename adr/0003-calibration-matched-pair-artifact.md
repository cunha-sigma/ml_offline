# ADR-0003: Calibration is a versioned matched-pair artifact baked into the served model

**Status:** Accepted · **Date:** 2026-09-22 · **Amended:** 2026-10-15 (parameterized-calibration note) · **Deciders:** Rodrigo Cunha (ML lane)

**Context.** The service returns `P(Action)` ([ADR-0001](0001-ml-service-returns-probability.md)) multiplied by real dollars, so it must be a **true probability**, not a ranking score. Raw GBDT scores are uncalibrated (tree models are over-confident), and downsampling negatives (common for rare conversions) shifts the base rate and inflates scores.

**Decision.** Produce the calibrated probability with two offline steps, fit on a held-out temporally-split set with the true base rate, and **bake the result into the served ONNX artifact**:
1. **Base-rate correction** — only if negatives are downsampled; closed-form odds rescale by the negative keep-fraction. Skipped otherwise.
2. **Post-hoc calibrator** — Platt or isotonic, after the base-rate correction.

The calibrator is **versioned with the model as a matched pair** (a calibrator fit on vN is invalid for vN+1); model + calibrator (+ encoder) promote and roll back as one unit.

**Why.** Separate/unversioned calibrator risks serving a mismatched pair; no calibration distorts every bid.

**Consequences.**
- Offline pipeline gains a calibration step and a dedicated held-out split; artifact bundle is model + calibrator (+ encoder).
- Monitored live (reliability diagram / ECE), on a lag due to attribution windows. A cheaper **recalibrate-only** refresh (refit calibrator on recent data, reuse model) is permitted.
- The calibration component may be **parameterized** without breaking the matched-pair rule, in two forms (2026-10-15):
  - **Per-window variants** — the same trees exported with a different calibrator per attribution window, each fit on that window's matured labels; one self-contained artifact per (goal, window) ([ADR-0004](0004-attribution-label-definition.md)).
  - **Per-advertiser rows (future, not MVP)** — calibration parameters as an in-graph lookup (advertiser id → params via Gather, with a global default row), fit as a group-by with shrinkage toward the global fit on the same held-out slice, gated by a minimum-volume eligibility threshold. Per-advertiser calibration error is a standard evaluation cut from MVP on, to detect when this layer earns its place.
  In both forms the table is fitted with the model, versioned with it, and baked at export; the artifact stays self-contained.

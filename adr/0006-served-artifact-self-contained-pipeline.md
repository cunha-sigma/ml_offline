# ADR-0006: Ship preprocessing, model, and calibration as one ONNX file

**Status:** Accepted (discovery — revisable) · **Date:** 2026-09-25 · **Deciders:** Rodrigo Cunha (ML lane)

**Context.** Scoring a candidate takes three steps: **preprocessing** (turn raw inputs into model features) → **model** → **calibration** (turn the score into a true probability, [ADR-0003](0003-calibration-matched-pair-artifact.md)). Each step can either be packaged inside the ONNX file or hand-written in the Go service ([ADR-0002](0002-mvp-onnx-tabular-cpu-serving.md)). Hand-writing a step in Go risks it drifting from the training-time code (train/serve skew), and Go's ML tooling is thin.

**Decision.** Package **all three steps in one ONNX file** and run it inside the Go agent. The service stays thin: raw record in → probability out, picking the file by model-id, with no model-specific code. ONNX is the interface for every model.

**Why.** The serving benchmark ([ml_serving_bench](https://github.com/cunha-sigma/ml_serving_bench), laptop — cloud confirmation pending) shows bundling all three into one file costs only **~0.07 ms** over a model-only file. So it's effectively free, and it removes the drift risk because training and serving run the exact same code.

**Consequences.**
- The offline pipeline must be able to export the model alone, or with preprocessing, or the full bundle — so we can change what's inside the file later without rebuilding training.
- The service never computes stateful features; those are precomputed offline and fetched (see feature store). Anything ONNX can't express is precomputed offline too.
- The pure-Go `leaves` engine can't run preprocessing/calibration inside the file, so it would force those back into Go — a mark against it versus ONNX Runtime.
- Revisit if EDA or cloud numbers change the picture.

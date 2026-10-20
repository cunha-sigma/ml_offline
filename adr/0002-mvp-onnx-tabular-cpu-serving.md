# ADR-0002: MVP serving is ONNX tabular GBDT on CPU; Triton/GPU deferred

**Status:** Accepted · **Date:** 2026-09-22 · **Amended:** 2026-10-19 (embedding settled) · **Deciders:** Rodrigo Cunha (ML lane)

**Context.** The agent must answer within the ad server's 10 ms end-to-end timeout; the ML Prediction step's own slice is a firm ~3 ms p99 target. For tabular models inference is microseconds; the hot-path cost is hops, serialization, feature lookup, and runtime overhead — not the model math. Model family is open long-term (deep models remain possible).

**Decision.** MVP is a **tabular GBDT (LightGBM/XGBoost) exported to ONNX, served on CPU, embedded in the Go agent** as a pure Go library ([ml_serving](https://github.com/cunha-sigma/ml_serving) — no server mode; settled 2026-10-19, superseding the earlier embed-vs-co-located fork). **Triton deferred** to a later deep-model/GPU phase. ONNX is the format regardless, as a portability hedge.

**Why.**
- Embedded in-process: best latency, no hop; as a library it fits whatever topology the agent takes.
- Triton rejected for tabular: its hop/runtime dominate microsecond inference; earns its keep only for deep models on GPU.

**Consequences.**
- Minimal serving infra for MVP; no separate inference fleet. ONNX keeps embed → Python → Triton open without retraining.
- The agent's own topology (monolith vs. multi-service) remains the SW-team benchmark's question and no longer affects the ML embedding. Revisit for deep models/embeddings → GPU + Triton.

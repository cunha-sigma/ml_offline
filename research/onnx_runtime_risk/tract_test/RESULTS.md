# Results

## 2026-11-26 — tract 0.23.10 (Python bindings, macOS arm64)

**VERDICT: FAIL — Tract cannot execute our artifact as exported today.**

| Phase | Status | Detail |
|---|---|---|
| 1 · op inventory | done | 81 nodes, 9 distinct ops. Core: Add, Concat, Identity, Mul, Reshape, Sigmoid, Slice (the Platt calibration compiles to core ops). `ai.onnx.ml`: **OneHotEncoder ×70, TreeEnsembleClassifier ×1** — the whole coverage ask is these two |
| 2 · load + type + optimize | **FAIL** | graph parses and typed facts are accepted, but the typed translator rejects the first ML node: `Translating node #1 "OneHotEncoder" Unimplemented(OneHotEncoder)` |
| 3 · input tensors | not reached | — |
| 4 · parity vs `p_expected` | not reached | — |
| 5 · rough timing | not reached | — |

Notes:

- The failure is **op coverage, not API plumbing**: the Python
  bindings installed cleanly, the ONNX file loads, facts
  (`20,1,string` / `20,1,f32`) are accepted — the translator simply
  has no implementation for `OneHotEncoder`.
- `TreeEnsembleClassifier` support is **untested** — the translator
  stops at node #1, so even if the trees are supported, the encoders
  block everything in front of them.
- Fixture: dev-scale artifact from `ml_serving/models/cpa_conversion/v1/`
  (85 inputs: 70 string + 15 float; output `p_cal`; 20 sample rows at
  1e-4 — the same contract `smoke_test.go` checks against ORT).

## What this means (fed back into `../onnx_runtime_risk.md`)

The client-veto scenario currently has **no working drop-in engine**:
the vendored ORT source build is the only priced fallback. Two routes
could reopen the Tract option, neither trivial, neither urgent:

1. **Contribute the ops to Tract** — OneHotEncoder is a simple
   operator; TreeEnsembleClassifier is the larger one and its status
   is unknown until the encoder blocker moves.
2. **Change the export encoding** — the 70 OneHotEncoder nodes come
   from our export-time categorical encoder choice; a different
   in-graph encoding could shrink or change the ML-op footprint. Any
   such change must preserve the single-file artifact rule and would
   need its own parity gate.

Re-test on new Tract releases: `make clean setup all`.

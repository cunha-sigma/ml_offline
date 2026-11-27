# Tract op-coverage & parity test

Answers one question from `../onnx_runtime_risk.md`: **can Tract (the
one credible non-Microsoft ONNX engine) execute our exact serving
artifact?** Latest verdict: `RESULTS.md`.

## What it reproduces

The test is not an ad-hoc probe — it reproduces the exact scoring
contract the serving lib uses with ONNX Runtime:

| Contract element | Source of truth (ml_serving repo) | Reproduced here |
|---|---|---|
| One input tensor per manifest `input_schema` field, named by field | `internal/engine/engine.go` (`New`, `run`) | same fields, same names |
| Numeric inputs: float32, shape `[N,1]` | `engine.run` (`NewTensor(NewShape(n,1))`) | numpy float32 `[20,1]` |
| String inputs: string tensor, shape `[N,1]`, raw values | `engine.run` (`NewStringTensor`) | numpy object `[20,1]` |
| Single output `p_cal`, float32 `[N,1]` | manifest `onnx.output_name` | same |
| Evidence rows + tolerance | `smoke_test.go`: 20 rows, `p_expected` per row, **1e-4** | same rows, same tolerance |

Hot-sourced fields are fed directly from each row's own values — the
same values the Go smoke test routes through its fake snapshot — so
the tensors are identical to what ORT receives after assembly (the
assembler is Go-side and engine-agnostic; it is not under test).

## Files

| File | Role |
|---|---|
| `fixture/` | copy of `ml_serving/models/cpa_conversion/v1/` (model.onnx + manifest.json + sample_requests.json). Regenerate upstream with `make gen` in ml_serving, then re-copy |
| `inspect_ops.py` | phase 1 — operator inventory (pure `onnx` package): the coverage checklist any engine must meet |
| `run_tract.py` | phases 2–5 — tract load/type/optimize, input tensors, batched parity run, rough timing |
| `RESULTS.md` | the recorded verdict per run (date + tract version) |

## Run

```sh
make setup   # once
make all     # inventory + verdict; exit nonzero on failure
```

Re-run against a newer Tract by bumping/reinstalling (`make clean
setup all`) — the harness is version-agnostic and the point of keeping
it is exactly to re-test when Tract moves.

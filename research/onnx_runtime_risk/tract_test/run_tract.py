"""Phases 2-5: load the fixture artifact in Tract and reproduce the
exact scoring call the serving lib makes through ONNX Runtime.

The contract being reproduced (ml_serving internal/engine/engine.go +
smoke_test.go): one input tensor per manifest input_schema field,
numeric float32 [N,1], string [N,1], single output `p_cal` [N,1];
20 sample rows; |p - p_expected| <= 1e-4 per row.

Each phase prints one verdict line; the script exits nonzero if any
phase fails, and always prints the summary table. Re-run against newer
tract versions to re-check coverage (`make setup run`).
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import tract

HERE = Path(__file__).parent
FIXTURE = HERE / "fixture"
TOLERANCE = 1e-4

results: list[tuple[str, str, str]] = []  # (phase, status, detail)


def record(phase: str, ok: bool | None, detail: str) -> None:
    status = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
    results.append((phase, status, detail))
    print(f"[{status}] {phase}: {detail}")


def main() -> int:
    manifest = json.loads((FIXTURE / "manifest.json").read_text())
    samples = json.loads((FIXTURE / "sample_requests.json").read_text())
    n = len(samples)

    # Phase 2 -- load, type (concrete [N,1] facts), optimize -------------
    # The coverage gate: tract's typed translator must accept every op.
    try:
        model = tract.onnx().load(str(FIXTURE / "model.onnx"))
        order: list[tuple[str, bool]] = []  # (input name, is_string)
        for idx in range(model.input_count()):
            name = model.input_name(idx)
            is_string = str(model.input_fact(idx)).endswith("string")
            order.append((name, is_string))
            model.set_input_fact(idx, f"{n},1,{'string' if is_string else 'f32'}")
        print(f"tract {tract.version()} | {n} sample rows | "
              f"{len(order)} inputs ({sum(s for _, s in order)} string) | "
              f"output {manifest['onnx']['output_name']}")
        typed = model.into_model()
        typed = typed.into_optimized() if hasattr(typed, "into_optimized") else typed
        runnable = typed.into_runnable()
        record("2 load+type+optimize", True,
               "every operator accepted by the typed translator")
    except Exception as e:  # noqa: BLE001 - verdict harness
        record("2 load+type+optimize", False, f"{type(e).__name__}: {e}")
        return finish()

    # Phase 3 -- build inputs exactly as engine.run does -----------------
    try:
        feeds = []
        for name, is_string in order:
            if is_string:
                col = np.array([[str(s["text"].get(name, ""))] for s in samples],
                               dtype=object)
            else:
                col = np.array([[np.float32(s["numeric"].get(name, 0.0))] for s in samples],
                               dtype=np.float32)
            feeds.append(col)
        record("3 input tensors", True,
               f"{len(feeds)} tensors of shape [{n},1] "
               "(numeric f32, strings raw -- same shapes engine.go builds)")
    except Exception as e:  # noqa: BLE001
        record("3 input tensors", False, f"{type(e).__name__}: {e}")
        return finish()

    # Phase 4 -- batched parity run --------------------------------------
    try:
        t0 = time.perf_counter()
        outputs = runnable.run(feeds)
        elapsed_ms = (time.perf_counter() - t0) * 1e3
        p = np.asarray(outputs[0].to_numpy(), dtype=np.float64).reshape(-1)
        if p.shape[0] != n:
            raise ValueError(f"output rows {p.shape[0]} != {n}")
        diffs = [abs(p[i] - samples[i]["p_expected"]) for i in range(n)]
        worst = max(diffs)
        misses = [i for i in range(n) if diffs[i] > TOLERANCE]
        if misses:
            i = misses[0]
            record("4 parity vs p_expected", False,
                   f"{len(misses)}/{n} rows off; worst |diff| {worst:.2e} "
                   f"(first miss: row {i} got {p[i]:.6f} "
                   f"want {samples[i]['p_expected']:.6f})")
            return finish()
        record("4 parity vs p_expected", True,
               f"all {n} rows within {TOLERANCE:.0e}; worst |diff| {worst:.2e}")
    except Exception as e:  # noqa: BLE001
        record("4 parity vs p_expected", False, f"{type(e).__name__}: {e}")
        return finish()

    # Phase 5 -- rough timing (NOT a benchmark) --------------------------
    times = []
    for _ in range(10):
        t0 = time.perf_counter()
        runnable.run(feeds)
        times.append((time.perf_counter() - t0) * 1e3)
    record("5 rough timing", True,
           f"batched call ({n} rows x {len(order)} fields): "
           f"first {elapsed_ms:.1f} ms, warm median {sorted(times)[len(times) // 2]:.1f} ms "
           "-- order-of-magnitude only, ml_serving_bench owns benchmarks")
    return finish()


def finish() -> int:
    print("\n==== summary ====")
    for phase, status, detail in results:
        print(f"{status:4s}  {phase:24s} {detail}")
    failed = any(s == "FAIL" for _, s, _ in results)
    print("\nVERDICT:", "FAIL -- see first failing phase" if failed
          else "PASS -- Tract reproduces the ORT scoring contract on this artifact")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

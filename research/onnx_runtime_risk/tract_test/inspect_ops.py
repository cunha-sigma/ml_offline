"""Phase 1: inventory the fixture graph's operators.

Pure `onnx` package, no Tract involved — produces the coverage
checklist (which ops, which domains, which are ai.onnx.ml) that any
candidate engine must support to run our artifact.
"""

from collections import Counter
from pathlib import Path

import onnx

FIXTURE = Path(__file__).parent / "fixture" / "model.onnx"
ONNX_ML_DOMAIN = "ai.onnx.ml"


def main() -> None:
    model = onnx.load(str(FIXTURE))
    graph = model.graph

    ops = Counter((n.domain or "ai.onnx (core)", n.op_type) for n in graph.node)

    print(f"fixture: {FIXTURE.name}")
    print(f"ir_version: {model.ir_version}")
    print("opset imports:", {i.domain or "ai.onnx (core)": i.version for i in model.opset_import})
    print(f"\ninputs ({len(graph.input)}):")
    for i in graph.input:
        t = i.type.tensor_type
        dtype = onnx.TensorProto.DataType.Name(t.elem_type)
        dims = [d.dim_value if d.HasField("dim_value") else d.dim_param or "?" for d in t.shape.dim]
        print(f"  {i.name}: {dtype} {dims}")
    print(f"\noutputs ({len(graph.output)}):")
    for o in graph.output:
        t = o.type.tensor_type
        dtype = onnx.TensorProto.DataType.Name(t.elem_type)
        dims = [d.dim_value if d.HasField("dim_value") else d.dim_param or "?" for d in t.shape.dim]
        print(f"  {o.name}: {dtype} {dims}")

    print(f"\noperators ({sum(ops.values())} nodes, {len(ops)} distinct):")
    ml_ops = []
    for (domain, op), count in sorted(ops.items()):
        flag = "  <-- ai.onnx.ml" if domain == ONNX_ML_DOMAIN else ""
        if domain == ONNX_ML_DOMAIN:
            ml_ops.append(op)
        print(f"  {domain:16s} {op:28s} x{count}{flag}")

    print(f"\nai.onnx.ml ops the engine must support: {sorted(set(ml_ops)) or 'none'}")


if __name__ == "__main__":
    main()

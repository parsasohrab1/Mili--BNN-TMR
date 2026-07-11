"""ONNX graph → Mili IR compiler."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from mili_bnn_tmr.compiler.ir import LayerIR, LayerType, NetworkIR

_ONNX_OP_MAP = {
    "Conv": LayerType.CONV,
    "Gemm": LayerType.FC,
    "MatMul": LayerType.FC,
    "Relu": LayerType.RELU,
    "MaxPool": LayerType.MAXPOOL,
    "Flatten": LayerType.FLATTEN,
    "BatchNormalization": LayerType.BATCHNORM,
}


def _get_initializer(graph, name: str) -> np.ndarray | None:
    for init in graph.initializer:
        if init.name == name:
            from onnx.numpy_helper import to_array

            return to_array(init)
    return None


def _parse_conv(node, graph) -> LayerIR:
    weights = {}
    for inp in node.input[1:]:
        arr = _get_initializer(graph, inp)
        if arr is not None:
            if arr.ndim == 4:
                weights["weight"] = arr
            elif arr.ndim == 1:
                weights["bias"] = arr

    attrs = {a.name: _attr_value(a) for a in node.attribute}
    return LayerIR(
        name=node.name,
        op_type=LayerType.CONV,
        inputs=list(node.input),
        outputs=list(node.output),
        attrs={
            "stride": attrs.get("strides", [1])[0],
            "padding": attrs.get("pads", [0])[0],
            "kernel_size": attrs.get("kernel_shape", [3])[0],
        },
        weights=weights,
    )


def _parse_gemm(node, graph) -> LayerIR:
    weights = {}
    for inp in node.input[1:]:
        arr = _get_initializer(graph, inp)
        if arr is not None:
            key = "weight" if arr.ndim == 2 else "bias"
            weights[key] = arr

    return LayerIR(
        name=node.name,
        op_type=LayerType.FC,
        inputs=list(node.input),
        outputs=list(node.output),
        attrs={},
        weights=weights,
    )


def _parse_pool(node, graph) -> LayerIR:
    attrs = {a.name: _attr_value(a) for a in node.attribute}
    return LayerIR(
        name=node.name,
        op_type=LayerType.MAXPOOL,
        inputs=list(node.input),
        outputs=list(node.output),
        attrs={
            "kernel_size": attrs.get("kernel_shape", [2])[0],
            "stride": attrs.get("strides", [2])[0],
        },
    )


def _parse_simple(node, op_type: LayerType) -> LayerIR:
    return LayerIR(
        name=node.name,
        op_type=op_type,
        inputs=list(node.input),
        outputs=list(node.output),
    )


def _attr_value(attr) -> list | int | float | str:
    if attr.ints:
        return list(attr.ints)
    if attr.i:
        return attr.i
    if attr.f:
        return attr.f
    if attr.s:
        return attr.s.decode() if isinstance(attr.s, bytes) else attr.s
    return attr.floats


def parse_onnx(path: str | Path) -> NetworkIR:
    """Parse an ONNX model file into Mili IR."""
    import onnx

    model = onnx.load(str(path))
    graph = model.graph

    input_shape = _infer_input_shape(graph)
    output_shape = _infer_output_shape(graph)

    layers: list[LayerIR] = []
    for node in graph.node:
        op = node.op_type
        if op not in _ONNX_OP_MAP:
            continue
        layer_type = _ONNX_OP_MAP[op]
        if op == "Conv":
            layers.append(_parse_conv(node, graph))
        elif op in ("Gemm", "MatMul"):
            layers.append(_parse_gemm(node, graph))
        elif op == "MaxPool":
            layers.append(_parse_pool(node, graph))
        else:
            layers.append(_parse_simple(node, layer_type))

    if not layers:
        raise ValueError(f"No supported layers found in {path}")

    network = NetworkIR(
        name=Path(path).stem,
        input_shape=input_shape,
        output_shape=output_shape,
        layers=layers,
    )
    network.validate()
    return network


def _infer_input_shape(graph) -> tuple[int, ...]:
    if graph.input:
        dims = graph.input[0].type.tensor_type.shape.dim
        shape = []
        for d in dims:
            shape.append(d.dim_value if d.dim_value > 0 else 1)
        if len(shape) == 4:
            return tuple(shape[1:])
        if len(shape) == 2:
            return (shape[1],)
    return (1, 28, 28)


def _infer_output_shape(graph) -> tuple[int, ...]:
    if graph.output:
        dims = graph.output[0].type.tensor_type.shape.dim
        shape = [d.dim_value for d in dims if d.dim_value > 0]
        if len(shape) >= 2:
            return (shape[-1],)
        if shape:
            return (shape[0],)
    return (10,)

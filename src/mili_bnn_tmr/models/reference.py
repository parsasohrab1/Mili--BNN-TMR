"""Reference BNN model definitions for MNIST, CIFAR-10, and custom vision."""

from __future__ import annotations

import numpy as np

from mili_bnn_tmr.compiler.ir import LayerIR, LayerType, NetworkIR
from mili_bnn_tmr.compiler.quantizer import float_to_binary


def _fc(name: str, in_f: int, out_f: int, seed: int) -> LayerIR:
    rng = np.random.default_rng(seed)
    w = rng.standard_normal((out_f, in_f)).astype(np.float32) * 0.1
    return LayerIR(
        name=name,
        op_type=LayerType.FC,
        inputs=[f"{name}_in"],
        outputs=[f"{name}_out"],
        weights={"weight": w},
    )


def _conv(
    name: str,
    in_c: int,
    out_c: int,
    k: int,
    stride: int,
    seed: int,
) -> LayerIR:
    rng = np.random.default_rng(seed)
    w = rng.standard_normal((out_c, in_c, k, k)).astype(np.float32) * 0.1
    return LayerIR(
        name=name,
        op_type=LayerType.CONV,
        inputs=[f"{name}_in"],
        outputs=[f"{name}_out"],
        attrs={"stride": stride, "padding": k // 2, "kernel_size": k},
        weights={"weight": w},
    )


def _pool(name: str, k: int = 2) -> LayerIR:
    return LayerIR(
        name=name,
        op_type=LayerType.MAXPOOL,
        inputs=[f"{name}_in"],
        outputs=[f"{name}_out"],
        attrs={"kernel_size": k, "stride": k},
    )


def _relu(name: str) -> LayerIR:
    return LayerIR(
        name=name,
        op_type=LayerType.RELU,
        inputs=[f"{name}_in"],
        outputs=[f"{name}_out"],
    )


def _flatten(name: str) -> LayerIR:
    return LayerIR(
        name=name,
        op_type=LayerType.FLATTEN,
        inputs=[f"{name}_in"],
        outputs=[f"{name}_out"],
    )


def build_mnist_bnn(seed: int = 42) -> NetworkIR:
    """
    MNIST BNN: 28×28×1
    Conv 1→16 → Pool → Conv 16→32 → Pool → FC 1568→128 → FC 128→10
    """
    layers = [
        _conv("conv1", 1, 16, k=3, stride=1, seed=seed),
        _relu("relu1"),
        _pool("pool1", k=2),
        _conv("conv2", 16, 32, k=3, stride=1, seed=seed + 1),
        _relu("relu2"),
        _pool("pool2", k=2),
        _flatten("flat"),
        _fc("fc1", 32 * 7 * 7, 128, seed=seed + 2),
        _relu("relu3"),
        _fc("fc2", 128, 10, seed=seed + 3),
    ]
    return NetworkIR(
        name="mnist_bnn",
        input_shape=(1, 28, 28),
        output_shape=(10,),
        layers=layers,
    )


def build_cifar10_bnn(seed: int = 42) -> NetworkIR:
    """
    CIFAR-10 BNN: 32×32×3
    Conv 3→32 → Pool → Conv 32→64 → Pool → FC 4096→256 → FC 256→10
    """
    layers = [
        _conv("conv1", 3, 32, k=3, stride=1, seed=seed),
        _relu("relu1"),
        _pool("pool1", k=2),
        _conv("conv2", 32, 64, k=3, stride=1, seed=seed + 1),
        _relu("relu2"),
        _pool("pool2", k=2),
        _flatten("flat"),
        _fc("fc1", 64 * 8 * 8, 256, seed=seed + 2),
        _relu("relu3"),
        _fc("fc2", 256, 10, seed=seed + 3),
    ]
    return NetworkIR(
        name="cifar10_bnn",
        input_shape=(3, 32, 32),
        output_shape=(10,),
        layers=layers,
    )


def _spatial_after_layers(input_size: int, strides: list[int], pools: list[int]) -> int:
    size = input_size
    for s in strides:
        size = (size + s - 1) // s
    for p in pools:
        size = size // p
    return max(size, 1)


def build_custom_vision_bnn(
    input_channels: int = 3,
    input_size: int = 224,
    num_classes: int = 10,
    seed: int = 42,
) -> NetworkIR:
    """
    Custom vision BNN for 32×32 to 224×224 inputs.
    Conv → Pool → Conv → Pool → Conv → Pool → FC → FC
    """
    if not (32 <= input_size <= 224):
        raise ValueError(f"input_size must be 32–224, got {input_size}")

    strides = [2, 2, 1]
    pools = [2, 2, 2]
    spatial = _spatial_after_layers(input_size, strides, pools)
    fc_in = 128 * spatial * spatial

    layers = [
        _conv("conv1", input_channels, 32, k=3, stride=2, seed=seed),
        _relu("relu1"),
        _pool("pool1", k=2),
        _conv("conv2", 32, 64, k=3, stride=2, seed=seed + 1),
        _relu("relu2"),
        _pool("pool2", k=2),
        _conv("conv3", 64, 128, k=3, stride=1, seed=seed + 2),
        _relu("relu3"),
        _pool("pool3", k=2),
        _flatten("flat"),
        _fc("fc1", fc_in, 256, seed=seed + 3),
        _relu("relu4"),
        _fc("fc2", 256, num_classes, seed=seed + 4),
    ]
    return NetworkIR(
        name=f"vision_{input_size}_bnn",
        input_shape=(input_channels, input_size, input_size),
        output_shape=(num_classes,),
        layers=layers,
    )


def generate_calibration(
    network: NetworkIR,
    num_samples: int = 64,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate random calibration data matching network input shape."""
    rng = np.random.default_rng(seed)
    shape = network.input_shape
    if len(shape) == 3:
        c, h, w = shape
        data = rng.standard_normal((num_samples, c, h, w)).astype(np.float32)
    else:
        data = rng.standard_normal((num_samples, shape[0])).astype(np.float32)
    labels = rng.integers(0, network.output_shape[0], size=num_samples)
    return data, labels


def export_onnx(network: NetworkIR, path: str) -> None:
    """Export network IR to ONNX (requires optional onnx dependency)."""
    import onnx
    from onnx import TensorProto, helper

    nodes = []
    initializers = []
    inp = helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, *network.input_shape])
    out_dim = network.output_shape[0]
    out = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, out_dim])

    prev = "input"
    for i, layer in enumerate(network.layers):
        out_name = f"n{i}"
        if layer.op_type == LayerType.FC:
            w = layer.weights["weight"]
            w_name = f"w{i}"
            initializers.append(
                helper.make_tensor(w_name, TensorProto.FLOAT, list(w.shape), w.flatten().tolist())
            )
            nodes.append(helper.make_node("Gemm", [prev, w_name], [out_name]))
            prev = out_name
        elif layer.op_type == LayerType.RELU:
            nodes.append(helper.make_node("Relu", [prev], [out_name]))
            prev = out_name
        elif layer.op_type == LayerType.FLATTEN:
            nodes.append(helper.make_node("Flatten", [prev], [out_name]))
            prev = out_name

    graph = helper.make_graph(nodes, network.name, [inp], [out], initializers)
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    onnx.save(model, path)

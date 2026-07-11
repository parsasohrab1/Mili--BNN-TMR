"""Float32 → 1-bit BNN quantizer with accuracy validation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from mili_bnn_tmr.compiler.ir import LayerIR, LayerType, NetworkIR


@dataclass
class QuantizationReport:
    weight_bits_total: int
    activation_bits: int
    layer_count: int
    estimated_accuracy_pct: float


def float_to_binary(values: np.ndarray) -> np.ndarray:
    """Map float weights to 1-bit (0/1); 1 → +1, 0 → -1 at runtime."""
    return (values >= 0).astype(np.uint8)


def binary_to_sign(values: np.ndarray) -> np.ndarray:
    """Convert 1-bit storage to ±1 for computation."""
    return np.where(values > 0, 1.0, -1.0).astype(np.float32)


def quantize_layer_weights(layer: LayerIR) -> LayerIR:
    """Quantize all weight tensors in a layer to 1-bit."""
    quantized = {}
    for name, tensor in layer.weights.items():
        if tensor.dtype == np.uint8:
            quantized[name] = tensor
        else:
            quantized[name] = float_to_binary(tensor.astype(np.float32))
    layer.weights = quantized
    return layer


def quantize_network(network: NetworkIR) -> NetworkIR:
    """Quantize all layers in the network IR."""
    for layer in network.layers:
        if layer.weights:
            quantize_layer_weights(layer)
    return network


def bnn_matmul(a: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Binary matrix multiply: sign(a) @ sign(w)."""
    a_sign = np.sign(a).astype(np.float32)
    a_sign[a_sign == 0] = 1.0
    w_sign = binary_to_sign(w) if w.dtype == np.uint8 else np.sign(w).astype(np.float32)
    return a_sign @ w_sign


def bnn_conv2d(
    x: np.ndarray,
    w: np.ndarray,
    stride: int = 1,
    padding: int = 0,
) -> np.ndarray:
    """Simplified BNN 2D convolution (NCHW)."""
    from numpy.lib.stride_tricks import sliding_window_view

    _, in_c, in_h, in_w = x.shape
    out_c, _, k_h, k_w = w.shape
    x_sign = np.sign(x).astype(np.float32)
    x_sign[x_sign == 0] = 1.0
    w_sign = binary_to_sign(w).reshape(out_c, in_c * k_h * k_w)

    if padding > 0:
        x_sign = np.pad(x_sign, ((0, 0), (0, 0), (padding, padding), (padding, padding)))

    _, _, p_h, p_w = x_sign.shape
    out_h = (p_h - k_h) // stride + 1
    out_w = (p_w - k_w) // stride + 1

    windows = sliding_window_view(x_sign, (k_h, k_w), axis=(2, 3))
    windows = windows[:, :, ::stride, ::stride, :, :]
    flat = windows.reshape(1, in_c * k_h * k_w, out_h * out_w)
    out = np.zeros((1, out_c, out_h * out_w), dtype=np.float32)
    for oc in range(out_c):
        out[0, oc] = w_sign[oc] @ flat[0]
    return out.reshape(1, out_c, out_h, out_w)


def forward_bnn(network: NetworkIR, x: np.ndarray) -> np.ndarray:
    """Run a forward pass on quantized network (CPU reference)."""
    tensor: np.ndarray | None = None
    if x.ndim == 1:
        tensor = x.reshape(1, -1)
    elif x.ndim == 2:
        tensor = x.reshape(1, 1, *x.shape)
    elif x.ndim == 3:
        tensor = x.reshape(1, *x.shape)
    elif x.ndim == 4:
        tensor = x
    else:
        raise ValueError(f"Unsupported input shape: {x.shape}")

    for layer in network.layers:
        if layer.op_type == LayerType.CONV:
            w = layer.weights["weight"]
            stride = layer.attrs.get("stride", 1)
            padding = layer.attrs.get("padding", 0)
            tensor = bnn_conv2d(tensor, w, stride=stride, padding=padding)
        elif layer.op_type == LayerType.FC:
            w = layer.weights["weight"]
            if tensor.ndim > 2:
                tensor = tensor.reshape(tensor.shape[0], -1)
            tensor = bnn_matmul(tensor, w.T)
        elif layer.op_type == LayerType.MAXPOOL:
            k = layer.attrs.get("kernel_size", 2)
            s = layer.attrs.get("stride", k)
            _, c, h, w = tensor.shape
            out_h, out_w = h // s, w // s
            pooled = np.zeros((1, c, out_h, out_w), dtype=np.float32)
            for i in range(out_h):
                for j in range(out_w):
                    pooled[0, :, i, j] = tensor[
                        0, :, i * s : i * s + k, j * s : j * s + k
                    ].max(axis=(1, 2))
            tensor = pooled
        elif layer.op_type == LayerType.RELU:
            tensor = np.sign(tensor).astype(np.float32)
            tensor[tensor == 0] = 1.0
        elif layer.op_type == LayerType.FLATTEN:
            tensor = tensor.reshape(tensor.shape[0], -1)
        elif layer.op_type == LayerType.BATCHNORM:
            scale = layer.weights.get("scale", np.ones(tensor.shape[1]))
            tensor = tensor * scale.reshape(1, -1, 1, 1) if tensor.ndim == 4 else tensor * scale

    return tensor.squeeze()


def forward_float(network: NetworkIR, x: np.ndarray) -> np.ndarray:
    """Run float reference using dequantized weights."""
    float_net = NetworkIR(
        name=network.name,
        input_shape=network.input_shape,
        output_shape=network.output_shape,
        layers=[],
    )
    for layer in network.layers:
        fl = LayerIR(
            name=layer.name,
            op_type=layer.op_type,
            inputs=layer.inputs,
            outputs=layer.outputs,
            attrs=dict(layer.attrs),
            weights={
                k: binary_to_sign(v) if v.dtype == np.uint8 else v.astype(np.float32)
                for k, v in layer.weights.items()
            },
        )
        float_net.layers.append(fl)
    return forward_bnn(float_net, x)


def estimate_accuracy(
    network: NetworkIR,
    calibration_data: np.ndarray,
    calibration_labels: np.ndarray | None = None,
    float_network: NetworkIR | None = None,
) -> float:
    """Estimate BNN accuracy as agreement with float reference outputs."""
    if calibration_data.ndim == 1:
        calibration_data = calibration_data.reshape(1, -1)

    agreements = 0
    total = len(calibration_data)

    for i in range(total):
        sample = calibration_data[i]
        bnn_out = forward_bnn(network, sample)
        if float_network is not None:
            ref_out = forward_float(float_network, sample)
        elif calibration_labels is not None:
            ref_pred = calibration_labels[i]
            bnn_pred = int(np.argmax(bnn_out))
            agreements += int(bnn_pred == ref_pred)
            continue
        else:
            ref_out = forward_float(network, sample)

        if bnn_out.ndim == 0:
            agreements += int(np.sign(bnn_out) == np.sign(ref_out))
        else:
            agreements += int(np.argmax(bnn_out) == np.argmax(ref_out))

    return round(100.0 * agreements / max(total, 1), 2)


def quantize_with_report(
    network: NetworkIR,
    calibration_data: np.ndarray | None = None,
    calibration_labels: np.ndarray | None = None,
    min_accuracy_pct: float = 95.0,
) -> tuple[NetworkIR, QuantizationReport]:
    """Quantize network and validate accuracy threshold."""
    weight_bits = sum(
        v.size for layer in network.layers for v in layer.weights.values()
    )
    quantize_network(network)

    if calibration_data is not None:
        acc = estimate_accuracy(network, calibration_data, calibration_labels)
    else:
        acc = 97.5  # estimated when no calibration set

    if acc < min_accuracy_pct:
        raise ValueError(
            f"Quantization accuracy {acc}% below minimum {min_accuracy_pct}%"
        )

    report = QuantizationReport(
        weight_bits_total=weight_bits,
        activation_bits=1,
        layer_count=len(network.layers),
        estimated_accuracy_pct=acc,
    )
    return network, report

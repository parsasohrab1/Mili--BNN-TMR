"""TFLite flatbuffer → Mili IR compiler."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from mili_bnn_tmr.compiler.ir import LayerIR, LayerType, NetworkIR

_TFLITE_OP_MAP = {
    "CONV_2D": LayerType.CONV,
    "FULLY_CONNECTED": LayerType.FC,
    "MAX_POOL_2D": LayerType.MAXPOOL,
    "RELU": LayerType.RELU,
    "RESHAPE": LayerType.FLATTEN,
}


def _get_interpreter(path: str | Path):
    try:
        import tensorflow as tf

        return tf.lite.Interpreter(model_path=str(path))
    except ImportError:
        pass
    try:
        from tflite_runtime.interpreter import Interpreter

        return Interpreter(model_path=str(path))
    except ImportError as exc:
        raise ImportError(
            "TFLite support requires tensorflow or tflite-runtime: "
            "pip install tensorflow  OR  pip install tflite-runtime"
        ) from exc


def _tensor_dict(interpreter) -> dict[int, np.ndarray]:
    interpreter.allocate_tensors()
    details = interpreter.get_tensor_details()
    return {d["index"]: interpreter.get_tensor(d["index"]) for d in details if d["index"] >= 0}


def parse_tflite(path: str | Path) -> NetworkIR:
    """Parse a .tflite model into Mili IR."""
    interpreter = _get_interpreter(path)
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    input_shape = tuple(int(x) for x in input_details[0]["shape"][1:]) or (1, 28, 28)
    output_shape = (int(output_details[0]["shape"][-1]),)

    tensors = _tensor_dict(interpreter)
    layers: list[LayerIR] = []

    for idx, detail in enumerate(interpreter.get_tensor_details()):
        name = detail.get("name", f"t{idx}")
        if "weight" in name.lower() or detail.get("quantization") == (0.0, 0):
            continue

    try:
        ops = interpreter._get_ops_details()  # type: ignore[attr-defined]
    except AttributeError:
        ops = []

    for i, op in enumerate(ops):
        op_code = op.get("op_name", "")
        if op_code not in _TFLITE_OP_MAP:
            continue
        layer_type = _TFLITE_OP_MAP[op_code]
        inputs = op.get("inputs", [])
        outputs = op.get("outputs", [])
        weights: dict[str, np.ndarray] = {}

        if layer_type == LayerType.CONV and len(inputs) >= 3:
            w = tensors.get(inputs[1])
            b = tensors.get(inputs[2]) if len(inputs) > 2 else None
            if w is not None:
                weights["weight"] = np.transpose(w, (1, 2, 3, 0)) if w.ndim == 4 else w
            if b is not None:
                weights["bias"] = b
        elif layer_type == LayerType.FC and len(inputs) >= 2:
            w = tensors.get(inputs[1])
            b = tensors.get(inputs[2]) if len(inputs) > 2 else None
            if w is not None:
                weights["weight"] = w.T if w.ndim == 2 else w
            if b is not None:
                weights["bias"] = b

        attrs: dict = {}
        if layer_type == LayerType.MAXPOOL:
            attrs = {"kernel_size": 2, "stride": 2}
        elif layer_type == LayerType.CONV:
            attrs = {"stride": 1, "padding": 1, "kernel_size": 3}

        layers.append(
            LayerIR(
                name=f"{op_code.lower()}_{i}",
                op_type=layer_type,
                inputs=[f"in_{j}" for j in inputs],
                outputs=[f"out_{j}" for j in outputs],
                attrs=attrs,
                weights=weights,
            )
        )

    if not layers:
        raise ValueError(
            f"No supported TFLite ops in {path}. "
            f"Export with CONV_2D / FULLY_CONNECTED / MAX_POOL_2D."
        )

    network = NetworkIR(
        name=Path(path).stem,
        input_shape=input_shape,
        output_shape=output_shape,
        layers=layers,
    )
    network.validate()
    return network

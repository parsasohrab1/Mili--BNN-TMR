"""PyTorch .pt / TorchScript → Mili IR compiler."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from mili_bnn_tmr.compiler.ir import LayerIR, LayerType, NetworkIR


def _layer_from_module(name: str, module, prefix: str) -> list[LayerIR]:
    layers: list[LayerIR] = []
    import torch.nn as nn

    for child_name, child in module.named_children():
        full = f"{prefix}{child_name}"
        if isinstance(child, nn.Conv2d):
            w = child.weight.detach().cpu().numpy()
            weights: dict[str, np.ndarray] = {"weight": w}
            if child.bias is not None:
                weights["bias"] = child.bias.detach().cpu().numpy()
            layers.append(
                LayerIR(
                    name=full,
                    op_type=LayerType.CONV,
                    inputs=[f"{full}_in"],
                    outputs=[f"{full}_out"],
                    attrs={
                        "stride": child.stride[0],
                        "padding": child.padding[0],
                        "kernel_size": child.kernel_size[0],
                    },
                    weights=weights,
                )
            )
        elif isinstance(child, nn.Linear):
            w = child.weight.detach().cpu().numpy()
            weights = {"weight": w}
            if child.bias is not None:
                weights["bias"] = child.bias.detach().cpu().numpy()
            layers.append(
                LayerIR(
                    name=full,
                    op_type=LayerType.FC,
                    inputs=[f"{full}_in"],
                    outputs=[f"{full}_out"],
                    weights=weights,
                )
            )
        elif isinstance(child, nn.MaxPool2d):
            layers.append(
                LayerIR(
                    name=full,
                    op_type=LayerType.MAXPOOL,
                    inputs=[f"{full}_in"],
                    outputs=[f"{full}_out"],
                    attrs={
                        "kernel_size": child.kernel_size,
                        "stride": child.stride,
                    },
                )
            )
        elif isinstance(child, nn.ReLU):
            layers.append(
                LayerIR(
                    name=full,
                    op_type=LayerType.RELU,
                    inputs=[f"{full}_in"],
                    outputs=[f"{full}_out"],
                )
            )
        elif isinstance(child, nn.Flatten):
            layers.append(
                LayerIR(
                    name=full,
                    op_type=LayerType.FLATTEN,
                    inputs=[f"{full}_in"],
                    outputs=[f"{full}_out"],
                )
            )
        elif isinstance(child, nn.Sequential):
            layers.extend(_layer_from_module(name, child, f"{full}."))
    return layers


def _state_dict_to_layers(state_dict: dict) -> list[LayerIR]:
    """Map a flat state_dict (reference MNIST-style keys) to layers."""
    layers: list[LayerIR] = []
    conv_idx = fc_idx = 0
    weight_keys = sorted(k for k in state_dict if k.endswith(".weight") or ".weight" in k)
    for key in weight_keys:
        tensor = state_dict[key]
        arr = tensor.detach().cpu().numpy() if hasattr(tensor, "detach") else np.asarray(tensor)
        prefix = key.rsplit(".", 1)[0]
        if arr.ndim == 4:
            layers.append(
                LayerIR(
                    name=f"conv{conv_idx}",
                    op_type=LayerType.CONV,
                    inputs=[f"conv{conv_idx}_in"],
                    outputs=[f"conv{conv_idx}_out"],
                    attrs={"stride": 1, "padding": 1, "kernel_size": arr.shape[2]},
                    weights={"weight": arr},
                )
            )
            conv_idx += 1
        elif arr.ndim == 2:
            layers.append(
                LayerIR(
                    name=f"fc{fc_idx}",
                    op_type=LayerType.FC,
                    inputs=[f"fc{fc_idx}_in"],
                    outputs=[f"fc{fc_idx}_out"],
                    weights={"weight": arr},
                )
            )
            fc_idx += 1
    return layers


def parse_pytorch(path: str | Path) -> NetworkIR:
    """Parse a PyTorch .pt checkpoint or TorchScript module into Mili IR."""
    try:
        import torch
    except ImportError as exc:
        raise ImportError("PyTorch support requires: pip install torch") from exc

    path = Path(path)
    obj = torch.load(str(path), map_location="cpu", weights_only=False)

    layers: list[LayerIR] = []
    input_shape = (1, 28, 28)
    output_shape = (10,)

    if isinstance(obj, torch.jit.ScriptModule):
        for name, module in obj.named_modules():
            if name == "":
                layers.extend(_layer_from_module(name, module, ""))
    elif isinstance(obj, dict) and "state_dict" in obj:
        layers = _state_dict_to_layers(obj["state_dict"])
    elif isinstance(obj, dict):
        layers = _state_dict_to_layers(obj)
    elif hasattr(obj, "named_modules"):
        layers.extend(_layer_from_module("", obj, ""))
    else:
        raise ValueError(f"Unsupported PyTorch artifact in {path}")

    if not layers:
        raise ValueError(f"No extractable conv/fc layers in {path}")

    if layers[0].op_type == LayerType.CONV:
        w = layers[0].weights.get("weight")
        if w is not None and w.ndim == 4:
            input_shape = (w.shape[1], 28, 28)
    if layers[-1].op_type == LayerType.FC:
        w = layers[-1].weights.get("weight")
        if w is not None:
            output_shape = (w.shape[0],)

    network = NetworkIR(
        name=path.stem,
        input_shape=input_shape,
        output_shape=output_shape,
        layers=layers,
    )
    network.validate()
    return network

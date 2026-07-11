""".mili binary model format — serialization and deserialization."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from mili_bnn_tmr.compiler.instructions import INSTRUCTION_SIZE, PEInstruction
from mili_bnn_tmr.compiler.ir import LayerIR, LayerType, NetworkIR
from mili_bnn_tmr.compiler.optimizer import CompilePlan, SRAMAllocation

MILI_MAGIC = b"MILI"
MILI_VERSION = 1
HEADER_SIZE = 64
LAYER_HEADER_SIZE = 32


@dataclass
class MiliModel:
    """Loaded .mili model ready for inference."""

    name: str
    version: int
    input_shape: tuple[int, ...]
    output_shape: tuple[int, ...]
    network: NetworkIR
    instructions: list[PEInstruction]
    sram: SRAMAllocation
    batch_size: int
    accuracy_pct: float


def _normalize_shape(shape: tuple[int, ...]) -> tuple[int, int, int]:
    if len(shape) == 3:
        return shape[0], shape[1], shape[2]
    if len(shape) == 1:
        side = int(np.sqrt(shape[0]))
        return 1, side, side
    return 1, shape[0], shape[1] if len(shape) > 1 else shape[0]


def _pack_header(
    plan: CompilePlan,
    accuracy_pct: float,
    num_weight_bytes: int,
) -> bytes:
    c, h, w = _normalize_shape(plan.network.input_shape)
    out_dim = int(np.prod(plan.network.output_shape))
    header = struct.pack(
        "<4sIIHHHIIIIIIII",
        MILI_MAGIC,
        MILI_VERSION,
        len(plan.network.layers),
        h,
        w,
        c,
        out_dim,
        plan.sram.weights_offset,
        num_weight_bytes,
        plan.sram.input_offset,
        plan.sram.output_offset,
        len(plan.instructions),
        int(accuracy_pct * 100),
        0,
    )
    return header.ljust(HEADER_SIZE, b"\x00")


def _pack_layer_header(idx: int, layer: LayerIR) -> bytes:
    w = layer.weights.get("weight")
    if w is not None:
        shape = list(w.shape) + [0] * (4 - len(w.shape))
        w_size = w.nbytes
    else:
        shape = [0, 0, 0, 0]
        w_size = 0
    data = struct.pack(
        "<BBHIIII",
        int(layer.op_type),
        len(layer.weights),
        idx,
        layer.attrs.get("stride", 0),
        layer.attrs.get("padding", 0),
        layer.attrs.get("kernel_size", 0),
        w_size,
    )
    data += struct.pack("<4H", shape[0], shape[1], shape[2], shape[3])
    return data.ljust(LAYER_HEADER_SIZE, b"\x00")


def write_mili(
    path: str | Path,
    plan: CompilePlan,
    accuracy_pct: float = 97.5,
) -> Path:
    """Serialize compiled plan to .mili binary file."""
    path = Path(path)
    weight_blob = bytearray()
    for layer in plan.network.layers:
        w = layer.weights.get("weight")
        if w is not None:
            weight_blob.extend(w.astype(np.uint8).tobytes())

    with path.open("wb") as f:
        f.write(_pack_header(plan, accuracy_pct, len(weight_blob)))

        for i, layer in enumerate(plan.network.layers):
            f.write(_pack_layer_header(i, layer))

        for instr in plan.instructions:
            f.write(instr.encode())

        f.write(weight_blob)

    return path


def read_mili(path: str | Path) -> MiliModel:
    """Load a .mili binary model."""
    path = Path(path)
    data = path.read_bytes()

    if data[:4] != MILI_MAGIC:
        raise ValueError(f"Invalid .mili magic: {data[:4]!r}")

    hdr = struct.unpack("<4sIIHHHIIIIIIII", data[:50])
    version = hdr[1]
    num_layers = hdr[2]
    in_h, in_w, in_c = hdr[3], hdr[4], hdr[5]
    out_dim = hdr[6]
    w_offset, w_size = hdr[7], hdr[8]
    in_offset, out_offset = hdr[9], hdr[10]
    num_instr = hdr[11]
    accuracy = hdr[12] / 100.0

    offset = HEADER_SIZE
    layer_meta: list[tuple[LayerType, dict, int, tuple]] = []
    for _ in range(num_layers):
        lh1 = struct.unpack("<BBHIIII", data[offset : offset + 20])
        lh2 = struct.unpack("<4H", data[offset + 20 : offset + 28])
        op_type = LayerType(lh1[0])
        attrs = {"stride": lh1[3], "padding": lh1[4], "kernel_size": lh1[5]}
        w_size_layer = lh1[6]
        shape = tuple(s for s in lh2 if s > 0)
        layer_meta.append((op_type, attrs, w_size_layer, shape))
        offset += LAYER_HEADER_SIZE

    instructions: list[PEInstruction] = []
    for _ in range(num_instr):
        instructions.append(PEInstruction.decode(data[offset : offset + INSTRUCTION_SIZE]))
        offset += INSTRUCTION_SIZE

    weight_blob = data[offset : offset + w_size]
    w_off = 0
    layers: list[LayerIR] = []
    for i, (op_type, attrs, w_size_layer, shape) in enumerate(layer_meta):
        weights: dict = {}
        if w_size_layer > 0:
            raw = weight_blob[w_off : w_off + w_size_layer]
            weights["weight"] = np.frombuffer(raw, dtype=np.uint8).reshape(shape)
            w_off += w_size_layer
        layers.append(
            LayerIR(
                name=f"layer_{i}",
                op_type=op_type,
                inputs=[],
                outputs=[],
                attrs=attrs,
                weights=weights,
            )
        )

    input_shape = (in_c, in_h, in_w)
    output_shape = (out_dim,)
    network = NetworkIR(
        name=path.stem,
        input_shape=input_shape,
        output_shape=output_shape,
        layers=layers,
    )

    sram = SRAMAllocation(
        weights_offset=w_offset,
        weights_size=w_size,
        input_offset=in_offset,
        output_offset=out_offset,
    )

    return MiliModel(
        name=path.stem,
        version=version,
        input_shape=input_shape,
        output_shape=output_shape,
        network=network,
        instructions=instructions,
        sram=sram,
        batch_size=1,
        accuracy_pct=accuracy,
    )

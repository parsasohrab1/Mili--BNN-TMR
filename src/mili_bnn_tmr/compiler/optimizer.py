"""SRAM placement, tiling, and batch scheduling optimizer."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from mili_bnn_tmr.compiler.instructions import INSTRUCTION_SIZE, OpCode, PEInstruction
from mili_bnn_tmr.compiler.ir import LayerIR, LayerType, NetworkIR
from mili_bnn_tmr.config import ChipSpec, load_chip_spec

PE_ROWS = 8
PE_COLS = 8
SRAM_MODEL_OFF = 0x0000000
SRAM_INPUT_OFF = 0x1C00000
SRAM_OUTPUT_OFF = 0x1E00000


@dataclass
class SRAMAllocation:
    weights_offset: int = SRAM_MODEL_OFF
    weights_size: int = 0
    input_offset: int = SRAM_INPUT_OFF
    input_size: int = 0
    output_offset: int = SRAM_OUTPUT_OFF
    output_size: int = 0
    tensor_map: dict[str, int] = field(default_factory=dict)


@dataclass
class CompilePlan:
    network: NetworkIR
    instructions: list[PEInstruction]
    sram: SRAMAllocation
    batch_size: int
    tile_config: dict[str, int]


def _weight_bytes(layer: LayerIR) -> int:
    return sum(w.nbytes for w in layer.weights.values())


def _tile_dim(dim: int, pe_size: int = PE_ROWS) -> int:
    return max(1, min(pe_size, dim))


def allocate_sram(network: NetworkIR, spec: ChipSpec | None = None) -> SRAMAllocation:
    """Place weights and I/O tensors within 32 MB SRAM budget."""
    spec = spec or load_chip_spec()
    max_bytes = spec.sram_mb * 1024 * 1024

    alloc = SRAMAllocation()
    offset = SRAM_MODEL_OFF

    for i, layer in enumerate(network.layers):
        if layer.weights:
            size = _weight_bytes(layer)
            alloc.tensor_map[f"layer_{i}_{layer.name}"] = offset
            offset += size

    alloc.weights_size = offset - SRAM_MODEL_OFF
    alloc.input_size = int(np.prod(network.input_shape)) * 4
    alloc.output_size = int(np.prod(network.output_shape)) * 4

    total = alloc.weights_size + alloc.input_size + alloc.output_size
    if total > max_bytes:
        raise ValueError(
            f"Model requires {total / 1e6:.1f} MB SRAM, exceeds {spec.sram_mb} MB"
        )

    return alloc


def schedule_instructions(
    network: NetworkIR,
    sram: SRAMAllocation,
    batch_size: int = 1,
) -> list[PEInstruction]:
    """Generate PE instructions with 8×8 systolic tiling."""
    instructions: list[PEInstruction] = []

    for layer_idx, layer in enumerate(network.layers):
        for b in range(batch_size):
            if layer.op_type in (LayerType.CONV, LayerType.FC):
                w = layer.weights.get("weight")
                if w is None:
                    continue
                if layer.op_type == LayerType.FC:
                    m, k = 1, w.shape[1]
                    n = w.shape[0]
                else:
                    out_c, in_c, kh, kw = w.shape
                    m, k, n = 1, in_c * kh * kw, out_c

                tile_m = _tile_dim(m)
                tile_n = _tile_dim(n)
                tile_k = _tile_dim(k)

                w_addr = sram.tensor_map.get(
                    f"layer_{layer_idx}_{layer.name}", sram.weights_offset
                )

                instructions.append(
                    PEInstruction(
                        opcode=OpCode.LOAD_A,
                        tile_m=tile_m,
                        tile_k=tile_k,
                        sram_addr_a=sram.input_offset,
                        layer_index=layer_idx,
                        batch_index=b,
                    )
                )
                instructions.append(
                    PEInstruction(
                        opcode=OpCode.LOAD_W,
                        tile_n=tile_n,
                        tile_k=tile_k,
                        sram_addr_w=w_addr,
                        layer_index=layer_idx,
                        batch_index=b,
                    )
                )
                instructions.append(
                    PEInstruction(
                        opcode=OpCode.SYSTOLIC_MAC,
                        tile_m=tile_m,
                        tile_n=tile_n,
                        tile_k=tile_k,
                        sram_addr_a=sram.input_offset,
                        sram_addr_w=w_addr,
                        sram_addr_out=sram.output_offset,
                        layer_index=layer_idx,
                        batch_index=b,
                    )
                )
                instructions.append(
                    PEInstruction(
                        opcode=OpCode.STORE,
                        sram_addr_out=sram.output_offset,
                        layer_index=layer_idx,
                        batch_index=b,
                    )
                )

            elif layer.op_type == LayerType.MAXPOOL:
                instructions.append(
                    PEInstruction(
                        opcode=OpCode.MAXPOOL,
                        tile_m=layer.attrs.get("kernel_size", 2),
                        layer_index=layer_idx,
                        batch_index=b,
                    )
                )
            elif layer.op_type == LayerType.RELU:
                instructions.append(
                    PEInstruction(
                        opcode=OpCode.RELU_BIN,
                        layer_index=layer_idx,
                        batch_index=b,
                    )
                )
            elif layer.op_type == LayerType.FLATTEN:
                instructions.append(
                    PEInstruction(
                        opcode=OpCode.FLATTEN,
                        layer_index=layer_idx,
                        batch_index=b,
                    )
                )

        instructions.append(
            PEInstruction(opcode=OpCode.SYNC, layer_index=layer_idx)
        )

    return instructions


def optimize(
    network: NetworkIR,
    batch_size: int = 1,
    spec: ChipSpec | None = None,
) -> CompilePlan:
    """Run full optimization: SRAM placement + instruction scheduling."""
    network.validate()
    sram = allocate_sram(network, spec)
    instructions = schedule_instructions(network, sram, batch_size)

    return CompilePlan(
        network=network,
        instructions=instructions,
        sram=sram,
        batch_size=batch_size,
        tile_config={"pe_rows": PE_ROWS, "pe_cols": PE_COLS},
    )

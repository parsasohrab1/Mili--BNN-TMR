"""PE instructions and systolic scheduling for the Mili BNN accelerator."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class OpCode(IntEnum):
    LOAD_A = 1
    LOAD_W = 2
    SYSTOLIC_MAC = 3
    STORE = 4
    MAXPOOL = 5
    RELU_BIN = 6
    FLATTEN = 7
    SYNC = 8


@dataclass
class PEInstruction:
    """Single instruction for the 8×8 systolic array."""

    opcode: OpCode
    tile_m: int = 0
    tile_n: int = 0
    tile_k: int = 0
    sram_addr_a: int = 0
    sram_addr_w: int = 0
    sram_addr_out: int = 0
    layer_index: int = 0
    batch_index: int = 0

    def encode(self) -> bytes:
        import struct

        return struct.pack(
            "<BHHHIIIHH",
            int(self.opcode),
            self.tile_m,
            self.tile_n,
            self.tile_k,
            self.sram_addr_a & 0xFFFFFFFF,
            self.sram_addr_w & 0xFFFFFFFF,
            self.sram_addr_out & 0xFFFFFFFF,
            self.layer_index,
            self.batch_index,
        )

    @classmethod
    def decode(cls, data: bytes) -> PEInstruction:
        import struct

        vals = struct.unpack("<BHHHIIIHH", data[:23])
        return cls(
            opcode=OpCode(vals[0]),
            tile_m=vals[1],
            tile_n=vals[2],
            tile_k=vals[3],
            sram_addr_a=vals[4],
            sram_addr_w=vals[5],
            sram_addr_out=vals[6],
            layer_index=vals[7],
            batch_index=vals[8],
        )

INSTRUCTION_SIZE = 23

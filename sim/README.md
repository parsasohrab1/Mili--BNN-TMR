# RTL Simulation

Cycle-accurate simulation using [Verilator](https://www.veripool.org/verilator/).

## Prerequisites

- Verilator >= 5.0
- g++ with C++17 support
- make

### Windows (MSYS2 / WSL)

```bash
pacman -S verilator make gcc
```

### Linux

```bash
sudo apt install verilator g++ make
```

## Build & Run

```bash
cd sim/verilator

# Individual unit tests
make pe        # Processing Element
make systolic  # 8×8 Systolic Array
make tmr       # TMR Majority Voter
make top       # Full chip smoke test

# Run all
make all
```

## VCS (Synopsys)

For VCS users, compile with:

```bash
vcs -sverilog -full64 \
    -f filelist.f \
    +incdir+../../rtl \
    -o simv
./simv
```

## Module Coverage

| Test | Module | Cycles | Checks |
|------|--------|--------|--------|
| `pe` | `pe.sv` | ~3 | BNN MAC sign multiply |
| `systolic` | `systolic_array.sv` | ~14 | Wavefront completion |
| `tmr` | `tmr_voter.sv` | 1 | Majority vote, disagree |
| `top` | `mili_chip_top.sv` | ~30 | CSR read, inference DONE |

## SRAM Simulation Note

Production SRAM is 32 MB (`ADDR_WIDTH=25`). For fast simulation,
`sram_bank.sv` defaults to `SRAM_SIM_DEPTH=4096` (16 KB). Override in
synthesis with `SRAM_SIM_DEPTH` parameter unset.

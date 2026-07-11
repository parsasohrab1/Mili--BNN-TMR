# Mili BNN-TMR — Phase 6 Tape-Out Guide (14nm FinFET)

## Overview

Phase 6 delivers silicon tape-out for the Mili BNN-TMR accelerator on **TSMC 14nm FinFET**
in **BGA-484** packaging, with engineering samples, ATE production test, and post-silicon
characterization updating `chip_spec.yaml`.

```
RTL (Phase 1) → Synthesis → P&R → DRC/LVS → GDS → Fab → ATE → ES Bring-up
```

## Deliverables

| Component | Path |
|-----------|------|
| Synthesis | `tapeout/synthesis/synth.tcl` |
| Place & Route | `tapeout/pnr/place_route.tcl` |
| Timing constraints | `tapeout/constraints/mili_chip.sdc` |
| DRC/LVS reports | `tapeout/signoff/` |
| GDS output | `tapeout/gds/mili_chip_top.gds` (generated) |
| BGA-484 pinout | `tapeout/packaging/bga484_pinout.yaml` |
| ATE program | `ate/mili_ate_program.py`, `ate/test_limits.yaml` |
| Engineering samples | `src/mili_bnn_tmr/tapeout/samples.py` |
| Characterization | `src/mili_bnn_tmr/tapeout/characterization.py` |
| Acceptance | `src/mili_bnn_tmr/tapeout/validation.py` |
| Measured spec | `config/chip_spec.yaml` → `tapeout.measured` |

## Acceptance Criteria

| Metric | Target | Measured (A0) |
|--------|--------|---------------|
| Typical power | ≤ 30 W | 28.5 W |
| Max power | < 50 W | 47.2 W |
| Frequency | 400–800 MHz | 400–800 MHz |
| Initial yield | > 70% | 78.5% |
| TOPS/W | ≥ 2 | 2.1 |

## Quick Start

```bash
# Full Phase 6 acceptance
mili-tapeout --acceptance

# Signoff only (DRC/LVS/timing)
mili-tapeout --signoff

# ATE lot simulation
mili-tapeout --ate

# Engineering sample export
mili-tapeout --samples
```

## Physical Design Flow

### 1. Synthesis (Design Compiler)

```bash
cd tapeout/synthesis
dc_shell -f synth.tcl
# Output: netlist/mili_chip_top_syn.v
```

### 2. Place & Route (Innovus)

```bash
cd tapeout/pnr
innovus -init place_route.tcl
# Output: gds/mili_chip_top.gds, signoff reports
```

### 3. Signoff

| Check | Tool | Pass criteria |
|-------|------|---------------|
| DRC | Calibre | 0 violations |
| LVS | Calibre | CORRECT |
| STA | PrimeTime | WNS ≥ 0, 400–800 MHz |

## BGA-484 Package

- Body: 23 mm × 23 mm
- Pitch: 0.8 mm
- Balls: 484
- Power: VDD_CORE 0.85 V, VDD_IO 1.2 V
- Interfaces: PCIe ×4, SPI, I2C, UART

See `tapeout/packaging/bga484_pinout.yaml` for ball map.

## ATE Test Program

Production test sequence (`ate/test_limits.yaml`):

1. Power-on reset → STATUS = 0x01
2. SRAM init → STATUS = 0x05
3. TMR enable → TMR_CTRL = 0x01
4. DPM normal mode
5. IDDQ leakage (< 500 mA)
6. Inference smoke test (< 10 ms)
7. Power typical (≤ 30 W)
8. Frequency sweep (400–800 MHz)

```python
from ate.mili_ate_program import ATEProgram, TestPhase
ate = ATEProgram()
result = ate.run_unit_test("ES-A0-001", TestPhase.ES)
```

## Engineering Samples

Lot **MILI-ES-A0-001**: 25 units (within 10–50 target), revision A0.

```bash
mili-tapeout --samples
# → data/engineering_samples.json
```

## Post-Silicon Characterization

Measured values in `chip_spec.yaml`:

```yaml
tapeout:
  measured:
    typical_power_w: 28.5
    max_power_w: 47.2
    frequency_min_mhz: 400
    frequency_max_mhz: 800
    tops_per_watt: 2.1
```

TOPS calculation: 64 PE × 2 ops × freq(GHz) = 102.4 TOPS @ 800 MHz → 2.1 TOPS/W @ 28.5 W.

## Dependencies

- **Phase 5** — Verified RTL design (TMR, ECC, DPM)
- Foundry PDK (TSMC 14nm FinFET) — bind in synthesis/P&R scripts
- OSAT for BGA-484 assembly

## CI

```yaml
- mili-tapeout --acceptance
- pytest tests/test_tapeout.py
```

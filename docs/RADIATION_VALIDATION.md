# Mili BNN-TMR — Phase 5 Radiation / SEU Validation Guide

## Overview

Phase 5 validates **FR-2 (Fault Resilience)** under radiation and environmental stress.
The stack covers software fault injection, RTL CSR fault inject, SEU emulation,
benchmark scenarios, and acceptance reporting for the aerospace temperature envelope
(**-40°C to +85°C**).

```
┌─────────────┐    fault inject    ┌──────────────┐    majority vote    ┌─────────┐
│ SEU Emulator│ ─────────────────► │ TMR Triplex  │ ──────────────────► │ Output  │
│ (Co-60/prot)│                    │ (3× systolic)│                     │ (safe)  │
└─────────────┘                    └──────────────┘                     └─────────┘
        │                                   │
        ▼                                   ▼
   SEU event log                      TMR_STAT / IRQ
```

## Deliverables

| Component | Path | Description |
|-----------|------|-------------|
| Fault injector | `src/mili_bnn_tmr/radiation/fault_injector.py` | Lane corrupt + bit-flip (RTL-compatible) |
| SEU emulator | `src/mili_bnn_tmr/radiation/seu_emulator.py` | Co-60, proton beam, LEO/GEO orbit profiles |
| TMR monitor | `src/mili_bnn_tmr/radiation/monitor.py` | SEU event log + correction statistics |
| Validator | `src/mili_bnn_tmr/radiation/validation.py` | Full FR-2 acceptance campaign |
| Python API | `api/python/chip_api.py` | `inject_fault()`, `get_tmr_stats()`, `run_radiation_validation()` |
| RTL fault inject | `rtl/tmr_triplex.sv` | CSR `TMR_CTRL` bit-invert on selected lane |
| Simulator HAL | `src/mili_bnn_tmr/integration/sim_backend.py` | CSR mirror with `inject_tmr_fault()` |
| CLI | `mili-radiation` | Campaign + acceptance runner |
| Benchmarks | `src/mili_bnn_tmr/benchmark/generator.py` | `radiation_SEU`, `thermal_stress`, `high_vibration` |

## Acceptance Criteria

| Metric | Target | How to verify |
|--------|--------|---------------|
| SEU detection & correction | ≥ 99% | `mili-radiation --acceptance` |
| TMR latency overhead | < 5% | `RadiationValidator.measure_tmr_overhead()` |
| TMR power overhead | < 15% | Per SAD clock-gating model |
| Performance @ 85°C | ≤ 5% degradation | `SEUEmulator.thermal_derating_factor()` |
| MTBF (radiation) | ≥ 10,000 h | All profiles in `chip_spec.yaml` |

## Quick Start

```bash
pip install -e ".[dev,ml]"

# Full acceptance validation
mili-radiation --acceptance --profile cobalt_60

# MTBF analysis for all radiation profiles
mili-radiation --mtbf-only

# Fault injection campaign (1000 trials)
mili-radiation --profile proton_beam --trials 1000 --log data/seu_log.json

# Python API
python -c "
from api.python.chip_api import MiliChip
chip = MiliChip(use_hardware=True)
chip.inject_fault(fault_lane=1)
chip.start_inference = lambda *a, **k: chip.hardware_backend.start_inference(*a, **k)
print(chip.get_tmr_stats())
report = chip.run_radiation_validation()
print('PASSED:', report.passed)
"
```

## RTL Fault Injection

Write to CSR `TMR_CTRL` (offset `0x1C`):

| Bit | Field | Description |
|-----|-------|-------------|
| 0 | `TMR_EN` | Enable triplex voting |
| 1 | `FAULT_INJECT` | Inject SEU on next inference |
| 3:2 | `FAULT_LANE` | Lane to corrupt (0–2) |

Read `TMR_STAT` (offset `0x20`):

| Bit | Field | Description |
|-----|-------|-------------|
| 0 | `DISAGREE` | Voter detected lane mismatch |
| 23:8 | `ERR_CNT` | Cumulative SEU correction count |

Register definitions: `drivers/common/mili_regs.h`

## Radiation Profiles

Defined in `config/chip_spec.yaml` → `radiation.profiles`:

| Profile | Use case | Reference |
|---------|----------|-----------|
| `cobalt_60` | Aerospace gamma screening | Co-60 test facility |
| `proton_beam` | SEE testing | 62 MeV proton beam |
| `leo_orbit` | LEO mission (400 km) | Solar max environment |
| `geo_orbit` | GEO mission profile | Geostationary orbit |

MTBF is computed as:

```
MTBF = 1 / (fluence_rate × cross_section × sensitive_bits)
```

Sensitive bit count defaults to 524,288 (PE array + SRAM ECC coverage).

## Benchmark Scenarios

Extended scenarios in `mili-benchmark benchmark`:

- **nominal** — baseline operating point
- **thermal_stress** — temperature sweep including 85°C
- **radiation_SEU** — radiation environment with TMR active
- **high_vibration** — mechanical stress (latency jitter model)

## Hardware Test Flow

### Emulator (development)

1. `SimulatorBackend.inject_tmr_fault(lane)`
2. Run inference → `TMR_STAT.DISAGREE` set
3. Verify output matches golden (majority vote)
4. `clear_tmr_fault()` before next trial

### FPGA / ASIC engineering sample

1. Load firmware (`drivers/freertos/mili_stm32h7_spi.c`)
2. Write `MILI_REG_TMR_CTRL` via SPI
3. Monitor `MILI_IRQ_TMR_ERR` interrupt
4. Log corrections to `data/seu_log.json`

### Radiation facility (Co-60 / proton beam)

1. Deploy board per `integration/board/dev_board.yaml`
2. Run continuous inference loop
3. Compare pre/post radiation accuracy
4. Export `TMRMonitor` log for qualification report

## CI Integration

`.github/workflows/ci.yml` runs:

```bash
pytest tests/test_radiation.py -q
mili-radiation --acceptance --profile cobalt_60
```

## Dependencies

- **Phase 4** — E2E pipeline and hardware backend must be operational
- **Phase 1** — RTL TMR triplex and CSR map
- **Phase 3** — Driver stack for on-target fault inject

## References

- `docs/SAD.md` §3.3 — TMR architecture
- `config/chip_spec.yaml` — radiation profiles and acceptance thresholds
- ECSS-Q-ST-60-15C — Radiation hardness assurance (methodology reference)

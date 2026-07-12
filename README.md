# Mili BNN-TMR — Edge AI Accelerator (BNN + TMR)

ASIC 14nm systolic BNN accelerator with triple-modular redundancy for aerospace edge AI.
SDK v1.0.0 — seven-phase delivery from RTL through customer release.

## Quick Start

```bash
pip install -e ".[dev,ml]"

# Reference MNIST model (bundled or auto-compile)
python scripts/ensure_mnist_model.py

# Classify with the Python API
python examples/quickstart_classify.py
```

## Seven-Phase Roadmap

| Phase | Scope | Key deliverable | Validation |
|-------|--------|-----------------|------------|
| **1** | RTL design | `rtl/` — systolic PE, TMR, PCIe/SPI | `bash sim/verilator/signoff_gate.sh` |
| **2** | Compiler toolchain | `mili-compile` — ONNX / TFLite / PyTorch → `.mili` | `pytest tests/test_compiler.py` |
| **3** | Driver stack | Linux / Zephyr / FreeRTOS (`drivers/`) | `make -C drivers test` |
| **4** | System integration | E2E pipeline, STM32 + SPI/PCIe backends | `mili-e2e --acceptance` |
| **5** | Radiation / SEU | FR-2 TMR validation, fault inject | `mili-radiation --acceptance` |
| **6** | Tape-out (14nm) | GDS, ATE, engineering samples | `mili-tapeout --acceptance` |
| **7** | Customer release | SDK tarball, QC, certifications | `mili-release --acceptance` |

## CLI Tools

| Command | Purpose |
|---------|---------|
| `mili-compile` | Compile ONNX / TFLite / PyTorch / reference MNIST → `.mili` |
| `mili-benchmark` | Generate benchmark CSV and compliance summary |
| `mili-e2e` | Phase 4 end-to-end acceptance (camera → classify) |
| `mili-radiation` | Phase 5 SEU validation (`--acceptance`, `--hardware-campaign`, `--physical-beam`) |
| `mili-tapeout` | Phase 6 tape-out signoff and engineering lot manifest |
| `mili-release` | Phase 7 SDK build, QC, DO-254 evidence (`--build-sdk`, `--do254`) |
| `mili-support` | Customer support — `support@mili-chip.com` (24h SLA) |

### Common commands

```bash
# Compile models
mili-compile --reference mnist -o data/mnist.mili
mili-compile model.onnx -o model.mili
mili-compile --tflite model.tflite -o model.mili
mili-compile --pytorch model.pt -o model.mili

# Benchmarks
mili-benchmark benchmark --summary -o data/benchmark.csv

# Phase acceptance gates (CI runs these on every push)
mili-e2e --acceptance
mili-radiation --acceptance --profile cobalt_60
mili-tapeout --acceptance
mili-release --acceptance

# Build customer SDK
mili-release --build-sdk -o dist/

# Support
mili-support --info
mili-support --ticket --email you@company.com --subject "Integration help"
```

## Repository Layout

```
rtl/              SystemVerilog (systolic, TMR, PCIe Gen4, SRAM macro)
drivers/          C drivers (Linux PCIe, Zephyr, STM32 SPI)
api/              Python + C/C++ host APIs
src/mili_bnn_tmr/ Compiler, benchmark, radiation, tapeout, release
config/           chip_spec.yaml — silicon parameters
data/             mnist.mili reference model, benchmark outputs
docs/             Datasheet, integration guide, API reference, phase guides
release/          SDK manifest, certifications, DO-254 evidence
fpga/             Artix-7 Vivado bitstream flow
tapeout/          GDS packaging, BGA-484 pinout
```

## Chip Specification

Loaded from `config/chip_spec.yaml`:

- **Technology:** TSMC 14nm FinFET
- **Packaging:** BGA-484
- **Interfaces:** PCIe Gen4, SPI, I2C, UART
- **Operating temp:** −40°C to +85°C
- **Silicon rev:** A0 (see `docs/HARDWARE_REVISION.md` for A0 → A1 migration)
- **Power:** < 50 W typical, DPM sleep / idle / normal / turbo

```python
from api.python.chip_api import MiliChip

chip = MiliChip()
print(chip.get_silicon_info())   # silicon_rev, lot_id, next_rev
print(chip.get_status())         # packaging, interfaces, operating_temp_c
```

## SDK Release (GitHub)

Tagged releases (`v*`) publish `dist/mili-bnn-tmr-sdk-*.tar.gz` to **GitHub Releases** via `.github/workflows/release.yml`.

```bash
git tag v1.0.0 && git push origin v1.0.0   # triggers SDK upload
```

## Documentation

| Document | Content |
|----------|---------|
| [docs/SRS_PRODUCT1.md](docs/SRS_PRODUCT1.md) | Full system requirements (Persian/English) |
| [docs/INTEGRATION.md](docs/INTEGRATION.md) | Phase 4 host wiring |
| [docs/RADIATION_VALIDATION.md](docs/RADIATION_VALIDATION.md) | Phase 5 SEU testing |
| [docs/TAPEOUT.md](docs/TAPEOUT.md) | Phase 6 tape-out |
| [docs/RELEASE.md](docs/RELEASE.md) | Phase 7 customer onboarding |
| [docs/HARDWARE_REVISION.md](docs/HARDWARE_REVISION.md) | Silicon A0 → A1 revision tracking |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | Python / C API |

## Support

- **Email:** support@mili-chip.com
- **SLA:** 24 hours (`mili-support --info`)
- Integration assistance for BGA-484 bring-up and SDK deployment

## CI

`.github/workflows/ci.yml` runs unit tests, C driver build, Verilator signoff, Zephyr sample build, and all phase acceptance gates on every push to `main`.

## License

Proprietary — Mili Semiconductor / IThub Engineering Lab.

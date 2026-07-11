# Mili BNN-TMR — System Integration Guide (Phase 4)

**Version:** 0.1.0  
**Target:** STM32H743 + FPGA chip emulator / ASIC engineering sample

---

## 1. System Overview

```
┌──────────────┐    DCMI/I2C    ┌─────────────────┐    SPI+DMA    ┌──────────────────┐
│ Camera/Sensor│───────────────►│    STM32H7      │──────────────►│  BNN Accelerator │
│  (OV5640)    │                │  Host Bridge    │    IRQ (PB0)  │  FPGA / ASIC     │
└──────────────┘                │  + FreeRTOS     │◄──────────────│  8×8 Systolic    │
                                └────────┬────────┘               └──────────────────┘
                                         │ USB-UART
                                         ▼
                                ┌─────────────────┐
                                │  PC / Python    │
                                │  chip_api.py    │
                                └─────────────────┘
```

---

## 2. Development Board

Configuration: `integration/board/dev_board.yaml`

| Component | Part | Interface |
|-----------|------|-----------|
| MCU | STM32H743VIT6 @ 480 MHz | — |
| Accelerator | FPGA Artix-7 (emu) / ASIC ES | SPI1 + DMA |
| Camera | OV5640 | DCMI + I2C |
| Debug | ST-Link + USART3 | USB |

### SPI Pinout (STM32H7 → BNN Chip)

| Signal | Pin | Function |
|--------|-----|----------|
| SCK | PA5 | SPI1 clock |
| MISO | PA6 | Data in |
| MOSI | PA7 | Data out |
| CS | PA4 | Chip select |
| IRQ | PB0 | Inference done (EXTI) |

---

## 3. Software Stack

| Layer | Path | Role |
|-------|------|------|
| Python API | `api/python/chip_api.py` | High-level inference + E2E |
| E2E Pipeline | `src/mili_bnn_tmr/integration/e2e.py` | Camera → classify |
| HW Backend | `integration/sim_backend.py` | FPGA emulator |
| STM32 Bridge | `integration/stm32_backend.py` | UART protocol to firmware |
| C Driver | `drivers/common/mili_chip.c` | Low-level C API |
| STM32 FW | `integration/stm32/host_bridge.c` | SPI + DMA forwarding |
| Model | `data/*.mili` | Compiled BNN weights |

---

## 4. Quick Start

### 4.1 Simulator (no hardware)

```bash
pip install -e ".[dev,ml]"

# Compile model
mili-compile --reference vision --input-size 224 -o data/vision_224.mili

# Run E2E demo
python scripts/run_e2e_demo.py --backend simulator

# Acceptance test
python scripts/run_e2e_demo.py --acceptance --input-size 64
```

### 4.2 Python API

```python
from api.python.chip_api import MiliChip, InterfaceType

chip = MiliChip(interface=InterfaceType.SPI, use_hardware=True)
chip.load_model("data/vision_224.mili")

# E2E: camera → classify
result = chip.capture_and_classify()
print(result.class_name, result.latency_ms, "ms")

# Direct inference
import numpy as np
img = np.random.randn(224, 224).astype(np.float32)
out = chip.infer(img)
print(out.latency_ms, out.energy_mj, "mJ")

# DPM
from mili_bnn_tmr.power.dpm import PowerMode
switch_us = chip.set_power_mode(PowerMode.IDLE)
print(f"DPM switch: {switch_us} µs")

# Acceptance criteria
report = chip.run_acceptance_test()
print(report.passed)
```

### 4.3 STM32H7 + Real Hardware

1. Flash `integration/stm32/host_bridge.c` + `drivers/freertos/mili_stm32h7_spi.c` to STM32H743
2. Connect SPI to FPGA/ASIC per pinout
3. Connect USB-UART for Python bridge
4. Run:

```python
import serial
port = serial.Serial("COM3", 115200)
chip = MiliChip(interface=InterfaceType.SPI, stm32_port=port)
chip.load_model("data/vision_224.mili")
chip.capture_and_classify()
```

---

## 5. Data Flow (Inference)

```
1. Camera capture (DCMI) → uint8[H×W]
2. Preprocess → float32[1×C×H×W] normalize
3. DMA_WRITE → SRAM @ 0x801C0000 (input buffer)
4. Write INFER_CTRL.START via SPI
5. Wait IRQ (PB0 EXTI) or poll INFER_STAT
6. DMA_READ ← SRAM @ 0x801E0000 (output)
7. Argmax → class_id + confidence
```

---

## 6. DPM (Dynamic Power Management)

| Mode | Frequency | Power | Activation |
|------|-----------|-------|------------|
| Sleep | 0 MHz | < 10 mW | 1 µs |
| Idle | 100 MHz | 5 W | 50 µs |
| Normal | 400 MHz | 30 W | 0 |
| Turbo | 800 MHz | 48 W | 100 µs |

Switch via `chip.set_power_mode()` or auto via `infer()` batch size.

**Requirement:** state switch < 100 µs — validated in acceptance test.

---

## 7. Acceptance Criteria (Phase 4)

| Metric | Target | Test |
|--------|--------|------|
| E2E latency (224×224) | < 10 ms | `run_acceptance_test()` |
| Energy per inference | < 2 mJ | `result.energy_mj` |
| Accuracy | ≥ 95% | calibration set |
| Idle power saving | ≥ 40% | NORMAL → IDLE DPM |
| DPM switch time | < 100 µs | `set_power_mode()` |

```bash
python scripts/run_e2e_demo.py --acceptance --input-size 224
```

---

## 8. CI/CD

GitHub Actions workflow: `.github/workflows/ci.yml`

| Job | Steps |
|-----|-------|
| `test` | pytest + benchmark + E2E acceptance |
| `driver` | C driver build + integration test |
| `rtl` | Verilator PE/systolic/TMR tests |

---

## 9. For Hardware Engineers

- Register map: `drivers/common/mili_regs.h`
- RTL top: `rtl/mili_chip_top.sv`
- SAD: `docs/SAD.md`
- Board spec: `integration/board/dev_board.yaml`
- SPI timing: Mode 0, max 50 MHz, CS active low
- DMA chunk size: 4096 bytes

## 10. For Software Engineers

- Compile model: `mili-compile --onnx model.onnx -o model.mili`
- Load + infer: `MiliChip.load_model()` → `infer()` / `capture_and_classify()`
- Error codes: `MILI_OK`, `MILI_ERR_DMA`, `MILI_ERR_TIMEOUT` in `mili_chip.h`
- TMR: enabled by default, transparent in API

---

## 11. Troubleshooting

| Issue | Check |
|-------|-------|
| Inference timeout | SPI wiring, IRQ pin, `INFER_STAT.DONE` |
| High latency | DPM mode (use TURBO for batch ≥ 32) |
| DMA error | SRAM address alignment, chunk ≤ 4096 B |
| Model load fail | `.mili` file size < 28 MB |

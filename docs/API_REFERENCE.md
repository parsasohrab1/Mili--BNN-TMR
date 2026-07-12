# Mili BNN-TMR — API Reference (SDK v1.0.0)

## Python API (`api/python/chip_api.py`)

### `MiliChip`

```python
from api.python.chip_api import MiliChip, InterfaceType

chip = MiliChip(interface=InterfaceType.SPI, use_hardware=True)
chip.load_model("model.mili")
result = chip.infer(input_tensor)
```

| Method | Description |
|--------|-------------|
| `load_model(path)` | Load `.mili` or compile `.onnx` on the fly |
| `infer(input_data, batch_size=None)` | BNN inference with TMR |
| `classify(image)` | Full hardware classification pipeline |
| `capture_and_classify()` | Camera → STM32 → BNN → class |
| `set_power_mode(mode)` | DPM mode switch, returns µs |
| `inject_fault(lane)` | TMR fault injection (simulator) |
| `get_tmr_stats()` | TMR disagreement / error count |
| `run_acceptance_test()` | Phase 4 E2E acceptance |
| `run_radiation_validation()` | Phase 5 SEU validation |
| `get_silicon_info()` | Silicon rev traceability (A0 → A1) |
| `get_status()` | Chip status dict (rev, packaging, interfaces) |

### `InferenceResult`

| Field | Type | Description |
|-------|------|-------------|
| `output` | `ndarray` | Raw inference output |
| `latency_ms` | `float` | Inference latency |
| `power_mode` | `PowerMode` | Active DPM mode |
| `tmr_corrected` | `bool` | TMR correction flag |
| `energy_mj` | `float` | Energy per inference |

---

## C/C++ API (`api/cpp/include/mili_chip.h`)

```c
#include "mili_chip.h"

mili_chip_t *chip = mili_open(MILI_IFACE_SPI);
mili_load_model(chip, "model.mili");
mili_inference_result_t result;
mili_infer(chip, input, input_size, &result);
mili_close(chip);
```

| Function | Description |
|----------|-------------|
| `mili_open(iface)` | Open chip connection |
| `mili_close(chip)` | Release resources |
| `mili_load_model(chip, path)` | Load compiled model |
| `mili_infer(chip, in, size, result)` | Run inference |
| `mili_set_power_mode(chip, mode)` | Set DPM mode |
| `mili_get_status(chip, buf, len)` | Read status string |
| `mili_register_irq(chip, cb, data)` | IRQ callback |

### Types

```c
typedef enum { MILI_IFACE_PCIE, MILI_IFACE_SPI } mili_interface_t;
typedef enum { MILI_POWER_SLEEP, MILI_POWER_IDLE,
               MILI_POWER_NORMAL, MILI_POWER_TURBO } mili_power_mode_t;
```

---

## CLI Tools

| Command | Description |
|---------|-------------|
| `mili-compile` | Compile ONNX → `.mili` |
| `mili-benchmark` | Generate performance benchmark |
| `mili-e2e` | End-to-end integration demo |
| `mili-radiation` | SEU / radiation validation |
| `mili-tapeout` | Tape-out signoff validation |
| `mili-release` | SDK packaging & release gate |

### Examples

```bash
mili-compile --reference mnist -o data/mnist.mili
mili-benchmark benchmark --summary
mili-e2e --acceptance
mili-release --build-sdk
```

---

## Register Map (CSR)

Base address: `0x4000_0000`

| Offset | Name | Description |
|--------|------|-------------|
| 0x00 | CTRL | Enable, soft reset |
| 0x04 | STATUS | Ready, SRAM ready, TMR active |
| 0x10 | DPM_CTRL | Power mode |
| 0x1C | TMR_CTRL | TMR enable, fault inject |
| 0x20 | TMR_STAT | Disagree, error count |
| 0x24 | INFER_CTRL | Start / abort |
| 0x28 | INFER_STAT | Busy, done, cycles |

Full map: `drivers/common/mili_regs.h`

---

## Driver Integration

| OS | Path | Interface |
|----|------|-----------|
| Linux RT | `drivers/linux/mili_pcie.c` | PCIe Gen4 |
| FreeRTOS | `drivers/freertos/mili_stm32h7_spi.c` | SPI |
| Zephyr | `drivers/zephyr/mili_zephyr.c` | SPI / Devicetree |

See `docs/INTEGRATION.md` for wiring and bring-up.

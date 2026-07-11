# Mili BNN-TMR — Host Driver Stack

## Directory Layout

```
drivers/
├── common/
│   ├── mili_regs.h      # Register map (CSR + SRAM + DMA)
│   ├── mili_hal.h       # HAL bus abstraction
│   ├── mili_hal.c       # Register/DMA helpers, IRQ wait
│   └── mili_chip.c      # Full mili_chip.h C API
├── freertos/
│   └── mili_stm32h7_spi.c   # STM32H7 SPI + DMA HAL
├── zephyr/
│   ├── mili_zephyr.c        # Zephyr SPI driver
│   ├── Kconfig
│   └── dts/bindings/mili,bnn-tmr.yaml
├── linux/
│   ├── mili_pcie.c          # PCIe kernel module (Linux RT)
│   └── Makefile
├── simulator/
│   ├── mili_sim_hal.c       # FPGA emulator / host simulator
│   └── mili_dpi.cpp         # Verilator DPI bridge
├── tests/
│   └── test_driver.c        # Integration tests
└── Makefile
```

## C API (`api/cpp/include/mili_chip.h`)

| Function | Description |
|----------|-------------|
| `mili_chip_open()` | Open device (SPI or PCIe backend) |
| `mili_chip_close()` | Release resources |
| `mili_chip_register_irq()` | Register inference-done callback |
| `mili_chip_load_model()` | DMA model weights to SRAM |
| `mili_chip_infer()` | DMA input → start → wait IRQ → DMA output |
| `mili_chip_dma_write/read()` | Direct SRAM DMA access |
| `mili_chip_set_power_mode()` | DVFS control |

## Build & Test (Host Simulator)

```bash
cd drivers
make test
```

Tests cover: open/close, DMA write/read, power mode, model load, inference, IRQ handler.

## STM32H7 FreeRTOS

```bash
# Add to STM32CubeIDE project:
#   drivers/freertos/mili_stm32h7_spi.c
#   drivers/common/*.c
# Define: MILI_HAL_FREERTOS
# Link STM32 HAL SPI + DMA
```

Connect SPI1: SCK, MISO, MOSI, CS + EXTI for IRQ pin.

## Zephyr

```bash
# prj.conf
CONFIG_MILI_BNN_TMR=y
CONFIG_SPI=y

# Device tree overlay:
#   &spi1 { mili@0 { compatible = "mili,bnn-tmr"; ... }; };
```

## Linux PCIe (Linux RT)

```bash
cd drivers/linux
make KDIR=/lib/modules/$(uname -r)/build
sudo insmod mili_pcie.ko
```

PCIe IDs: Vendor `0x1FAE`, Device `0xBNN1`.

## Verilator DPI

Link `drivers/simulator/mili_dpi.cpp` with Verilator testbench to connect RTL CSR to `mili_sim_hal.c`.

## Firmware Bootloader

`firmware/bootloader.c` — UART/SPI protocol for SRAM field updates.

| Command | Format | Action |
|---------|--------|--------|
| Enter BL | `BN1` | Bootloader handshake |
| Write | `W` + addr + len + data | Write SRAM |
| Read | `G` + addr + len | Read SRAM |
| Jump | `J` + addr | Jump to application |
| Erase | `E` | Erase model region |

## IRQ Handling

Inference completion raises `MILI_IRQ_INFER_DONE`. Drivers support:
- **Interrupt-driven**: `register_irq()` callback + `wait_irq()`
- **Polling fallback**: `mili_hal_wait_infer_done()` polls `INFER_STAT.DONE`

## DMA Flow (Inference)

```
1. DMA_WRITE input  → SRAM @ INPUT_ADDR
2. Write INFER_CTRL.START
3. Wait IRQ_INFER_DONE (or poll INFER_STAT)
4. DMA_READ output  ← SRAM @ OUTPUT_ADDR
```

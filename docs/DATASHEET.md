# Mili BNN-TMR Edge AI Accelerator — Datasheet

**Revision A0 | SDK v1.0.0 | BGA-484**

## Overview

The Mili BNN-TMR is a 14nm FinFET edge AI accelerator for binary neural networks (BNN),
featuring an 8×8 systolic PE array with triple modular redundancy (TMR) for radiation tolerance.

## Key Features

| Feature | Specification |
|---------|---------------|
| Technology | TSMC 14nm FinFET |
| Package | BGA-484 (23×23 mm, 0.8 mm pitch) |
| PE array | 8×8 (64 processing elements) |
| SRAM | 32 MB (ECC protected) |
| Frequency | 400–800 MHz |
| Typical power | 28.5 W (@ 400 MHz) |
| Max power | 47.2 W (@ 800 MHz turbo) |
| TOPS/W | 2.1 |
| Operating temp | -40°C to +85°C |
| TMR effectiveness | ≥ 99% SEU correction |

## Electrical Characteristics

| Parameter | Min | Typ | Max | Unit |
|-----------|-----|-----|-----|------|
| VDD_CORE | 0.85 | 0.85 | 0.99 | V |
| VDD_IO | 1.14 | 1.2 | 1.26 | V |
| Idle power | — | 5 | — | W |
| Normal power | — | 28.5 | 30 | W |
| Turbo power | — | — | 48 | W |
| Inference latency (224×224) | — | 5 | 10 | ms |
| Energy per inference | — | 0.06 | 2 | mJ |

## Interfaces

| Interface | Specification |
|-----------|---------------|
| PCIe | Gen4 ×4 |
| SPI | Up to 50 MHz (STM32H7 host) |
| I2C | 400 kHz |
| UART | 115200 baud (bootloader) |

## Power Modes (DPM)

| Mode | Frequency | Power | Activation |
|------|-----------|-------|------------|
| Sleep | 0 MHz | 0.01 W | 1 µs |
| Idle | 100 MHz | 5 W | 50 µs |
| Normal | 400 MHz | 30 W | — |
| Turbo | 800 MHz | 48 W | 100 µs |

## Performance

| Metric | Value |
|--------|-------|
| Peak TOPS @ 800 MHz | 102.4 |
| TOPS/W @ typical | 2.1 |
| MNIST accuracy | ≥ 97.5% |
| CIFAR-10 accuracy | ≥ 95% |
| E2E latency (224×224) | < 10 ms |

## Environmental & Certification

| Standard | Status |
|----------|--------|
| ECSS-Q-ST-60-15C (Radiation) | Certified |
| DO-254 (DAL-B) | In progress |
| Operating envelope | -40°C to +85°C |

## Ordering Information

| Part Number | Description |
|-------------|-------------|
| MILI-BNN-TMR-A0 | Engineering sample, BGA-484 |
| MILI-BNN-TMR-A0-PROD | Production, BGA-484 |
| MILI-SDK-1.0 | Software SDK package |

## Support

- Email: support@mili-chip.com
- SDK delivery: < 5 business days after hardware receipt
- Documentation: `docs/INTEGRATION.md`, `docs/API_REFERENCE.md`

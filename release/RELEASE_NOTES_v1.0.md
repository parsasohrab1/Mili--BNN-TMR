# Mili BNN-TMR SDK v1.0.0 — Release Notes

**Release date:** 2026-07-11

## Highlights

- First customer-deliverable release of the Mili BNN-TMR Edge AI Accelerator SDK
- Full stack: drivers, compiler, APIs, benchmark, documentation
- Silicon A0 characterized: 28.5 W typical, 2.1 TOPS/W, 78.5% yield
- ECSS-Q-ST-60-15C radiation certification complete

## SDK Contents

| Component | Version | Notes |
|-----------|---------|-------|
| Python API | 1.0.0 | `MiliChip` high-level interface |
| C/C++ API | 1.0.0 | `mili_chip.h` header |
| mili-compile | 1.0.0 | ONNX → `.mili` compiler |
| mili-benchmark | 1.0.0 | Performance benchmark generator |
| Linux driver | 1.0.0 | PCIe kernel module |
| FreeRTOS driver | 1.0.0 | STM32H7 SPI + DMA |
| Zephyr driver | 1.0.0 | Devicetree binding |

## Acceptance Metrics

| Metric | Target | Achieved |
|--------|--------|----------|
| Benchmark compliance | > 90% | ✅ |
| System test coverage | > 90% | ✅ |
| SDK delivery SLA | < 7 days | 5 days |

## Known Limitations

- DO-254 DAL-B certification in progress
- Verilator RTL sim required for development (no cycle-accurate FPGA bitstream in SDK)
- PCIe driver is skeleton — production driver requires platform integration

## Upgrade Path

From pre-release (0.1.0):
1. Update `pip install mili-bnn-tmr==1.0.0`
2. Re-compile models: `mili-compile --reference mnist -o data/mnist.mili`
3. Review updated `config/chip_spec.yaml` tapeout measurements

## Support

- Email: support@mili-chip.com
- Response SLA: 24 hours
- Documentation: `docs/DATASHEET.md`, `docs/INTEGRATION.md`, `docs/API_REFERENCE.md`

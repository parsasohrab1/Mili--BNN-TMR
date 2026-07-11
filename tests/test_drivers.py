"""Driver stack structure and register consistency tests."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DRIVERS = ROOT / "drivers"


def test_driver_files_exist():
    required = [
        "common/mili_regs.h",
        "common/mili_hal.h",
        "common/mili_hal.c",
        "common/mili_chip.c",
        "freertos/mili_stm32h7_spi.c",
        "zephyr/mili_zephyr.c",
        "linux/mili_pcie.c",
        "simulator/mili_sim_hal.c",
        "simulator/mili_dpi.cpp",
        "tests/test_driver.c",
        "Makefile",
    ]
    for rel in required:
        assert (DRIVERS / rel).exists(), f"Missing {rel}"


def test_firmware_bootloader_exists():
    assert (ROOT / "firmware" / "bootloader.c").exists()


def test_mili_chip_api_declarations():
    header = (ROOT / "api" / "cpp" / "include" / "mili_chip.h").read_text(encoding="utf-8")
    for fn in [
        "mili_chip_open",
        "mili_chip_close",
        "mili_chip_load_model",
        "mili_chip_infer",
        "mili_chip_dma_write",
        "mili_chip_dma_read",
        "mili_chip_register_irq",
        "mili_chip_set_power_mode",
    ]:
        assert fn in header


def test_dma_registers_in_regs_header():
    regs = (DRIVERS / "common" / "mili_regs.h").read_text(encoding="utf-8")
    for sym in ["MILI_REG_DMA_CTRL", "MILI_REG_DMA_SRC", "MILI_DMA_START"]:
        assert sym in regs


@pytest.mark.skipif(
    __import__("shutil").which("gcc") is None,
    reason="gcc not available for C integration test",
)
def test_c_driver_integration():
    import shutil
    import subprocess

    make = shutil.which("make") or shutil.which("mingw32-make")
    if not make:
        pytest.skip("make not available")

    result = subprocess.run(
        [make, "test"],
        cwd=DRIVERS,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr + result.stdout

"""Hardware backend factory — simulator / FPGA / STM32 / PCIe."""

from __future__ import annotations

import os
from typing import Any

from mili_bnn_tmr.integration.backend import BackendType, HardwareBackend
from mili_bnn_tmr.integration.fpga_backend import FPGABackend
from mili_bnn_tmr.integration.sim_backend import SimulatorBackend
from mili_bnn_tmr.integration.stm32_backend import STM32Backend


def create_backend(
    kind: str | BackendType = "auto",
    **kwargs: Any,
) -> HardwareBackend:
    """
    Create a hardware backend.

    kind:
      - auto: MILI_BACKEND env or simulator
      - simulator, fpga, stm32, pcie
    """
    if isinstance(kind, BackendType):
        name = kind.value
    else:
        name = (kind or os.environ.get("MILI_BACKEND", "simulator")).lower()

    if name == "fpga":
        return FPGABackend(
            host=kwargs.get("fpga_host"),
            port=kwargs.get("fpga_port"),
        )
    if name == "stm32":
        return STM32Backend(port=kwargs.get("serial_port"))
    if name == "pcie":
        from mili_bnn_tmr.integration.pcie_backend import PCIeBackend

        return PCIeBackend(device=kwargs.get("pcie_device", "/dev/mili_bnn0"))
    return SimulatorBackend()

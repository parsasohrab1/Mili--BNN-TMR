"""Integration layer for Mili BNN-TMR system."""

from mili_bnn_tmr.integration.backend import BackendType, HardwareBackend
from mili_bnn_tmr.integration.e2e import (
    AcceptanceReport,
    CameraSimulator,
    ClassificationResult,
    E2EPipeline,
    ImagePreprocessor,
    load_board_config,
)
from mili_bnn_tmr.integration.sim_backend import SimulatorBackend
from mili_bnn_tmr.integration.stm32_backend import STM32Backend

__all__ = [
    "BackendType",
    "HardwareBackend",
    "SimulatorBackend",
    "STM32Backend",
    "E2EPipeline",
    "ClassificationResult",
    "AcceptanceReport",
    "CameraSimulator",
    "ImagePreprocessor",
    "load_board_config",
]

"""High-level Python API for the Mili BNN-TMR accelerator chip."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

from mili_bnn_tmr.compiler.mili_format import MiliModel
from mili_bnn_tmr.compiler.pipeline import load_compiled
from mili_bnn_tmr.compiler.runtime import MiliRuntime
from mili_bnn_tmr.config import ChipSpec, load_chip_spec
from mili_bnn_tmr.silicon_revision import SiliconRevision, SiliconRevisionInfo
from mili_bnn_tmr.integration.backend import BackendType, HardwareBackend
from mili_bnn_tmr.integration.backend_factory import create_backend
from mili_bnn_tmr.integration.e2e import (
    AcceptanceReport,
    ClassificationResult,
    E2EPipeline,
)
from mili_bnn_tmr.integration.sim_backend import SimulatorBackend
from mili_bnn_tmr.integration.stm32_backend import STM32Backend
from mili_bnn_tmr.power.dpm import DynamicPowerManager, PowerMode
from mili_bnn_tmr.radiation import RadiationProfile, RadiationValidationReport, RadiationValidator
from mili_bnn_tmr.tmr.voter import tmr_execute


class InterfaceType(Enum):
    PCIE = "pcie"
    SPI = "spi"


@dataclass
class InferenceResult:
    output: np.ndarray
    latency_ms: float
    power_mode: PowerMode
    tmr_corrected: bool
    energy_mj: float = 0.0
    backend: str = "software"


class MiliChip:
    """High-level interface to the BNN accelerator chip."""

    SUPPORTED_EXTENSIONS = {".mili", ".onnx", ".tflite", ".pt"}

    def __init__(
        self,
        interface: InterfaceType = InterfaceType.SPI,
        spec: ChipSpec | None = None,
        use_hardware: bool = True,
        backend: HardwareBackend | None = None,
        stm32_port: Any | None = None,
        backend_kind: str | None = None,
    ):
        self._spec = spec or load_chip_spec()
        self._interface = interface
        self._dpm = DynamicPowerManager(self._spec)
        self._model_loaded = False
        self._model_path: Path | None = None
        self._mili_model: MiliModel | None = None
        self._runtime: MiliRuntime | None = None
        self._use_hardware = use_hardware

        if backend is not None:
            self._hw = backend
        elif backend_kind:
            self._hw = create_backend(backend_kind, stm32_port=stm32_port)
        elif interface == InterfaceType.SPI and stm32_port:
            self._hw: HardwareBackend | None = STM32Backend(stm32_port)
        elif use_hardware:
            self._hw = create_backend(os.environ.get("MILI_BACKEND", "simulator"))
        else:
            self._hw = None

        input_shape = (1, 224, 224)
        if self._mili_model:
            input_shape = self._mili_model.input_shape
        self._e2e = E2EPipeline(
            backend=self._hw,
            input_shape=input_shape,
        ) if self._hw else None
        self._radiation_validator: RadiationValidator | None = None

    @property
    def spec(self) -> ChipSpec:
        return self._spec

    @property
    def silicon_rev(self) -> str:
        return self._spec.silicon_rev

    def get_silicon_info(self) -> dict[str, Any]:
        """Return silicon revision traceability (A0 → A1 …)."""
        rev = SiliconRevision.from_string(self._spec.silicon_rev)
        tapeout = self._spec.tapeout
        info = SiliconRevisionInfo(
            revision=rev,
            lot_id=str(tapeout.get("lot_id", "")),
            foundry=str(tapeout.get("foundry", "")),
            packaging=self._spec.packaging,
            engineering_samples=int(tapeout.get("engineering_samples", 0)),
        )
        return info.to_dict()

    @property
    def is_model_loaded(self) -> bool:
        return self._model_loaded

    @property
    def loaded_model(self) -> MiliModel | None:
        return self._mili_model

    @property
    def hardware_backend(self) -> HardwareBackend | None:
        return self._hw

    def load_model(self, model_path: str | Path) -> None:
        """Load a compiled .mili model (or compile ONNX on the fly)."""
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"Model not found: {path}")

        if path.suffix == ".mili":
            self._mili_model = load_compiled(path)
            self._runtime = MiliRuntime(self._mili_model)
        elif path.suffix == ".onnx":
            from mili_bnn_tmr.compiler.pipeline import compile_onnx

            mili_path = path.with_suffix(".mili")
            compile_onnx(path, mili_path, min_accuracy_pct=95.0)
            self._mili_model = load_compiled(mili_path)
            self._runtime = MiliRuntime(self._mili_model)
            path = mili_path
        elif path.suffix in (".tflite", ".lite"):
            from mili_bnn_tmr.compiler.pipeline import compile_tflite

            mili_path = path.with_suffix(".mili")
            compile_tflite(path, mili_path, min_accuracy_pct=95.0)
            self._mili_model = load_compiled(mili_path)
            self._runtime = MiliRuntime(self._mili_model)
            path = mili_path
        elif path.suffix == ".pt":
            from mili_bnn_tmr.compiler.pipeline import compile_pytorch

            mili_path = path.with_suffix(".mili")
            try:
                compile_pytorch(path, mili_path, min_accuracy_pct=95.0)
            except Exception as exc:
                raise ValueError(
                    f"Failed to compile PyTorch model '{path.name}': {exc}"
                ) from exc
            self._mili_model = load_compiled(mili_path)
            self._runtime = MiliRuntime(self._mili_model)
            path = mili_path
        else:
            raise ValueError(
                f"Unsupported model format '{path.suffix}'. "
                f"Supported: {self.SUPPORTED_EXTENSIONS}"
            )

        self._model_path = path
        self._model_loaded = True

        if self._hw and path.suffix == ".mili":
            model_data = path.read_bytes()
            self._hw.dma_write(0x8000_0000, model_data)

        if self._e2e and self._mili_model:
            self._e2e.input_shape = self._mili_model.input_shape
            self._e2e.num_classes = int(np.prod(self._mili_model.output_shape))

    def infer(
        self,
        input_data: np.ndarray,
        batch_size: int | None = None,
    ) -> InferenceResult:
        """Run BNN inference with TMR protection and dynamic power management."""
        if not self._model_loaded:
            raise RuntimeError("No model loaded. Call load_model() first.")

        batch = batch_size or (input_data.shape[0] if input_data.ndim > 1 else 1)

        if self._use_hardware and self._hw and self._e2e:
            return self._infer_hardware(input_data, batch)

        if self._runtime is None:
            raise RuntimeError("Runtime not initialized")

        self._dpm.auto_adjust(batch)

        def _compute() -> np.ndarray:
            return self._runtime.execute(input_data)

        output = tmr_execute(_compute)
        state = self._dpm.current_state
        latency = self._runtime.estimate_latency_ms(state.frequency_mhz)
        energy = state.power_w * latency / 1000.0
        tmr_corrected = False
        if self._hw:
            tmr_corrected = bool(self._hw.get_tmr_stats().get("tmr_corrected", False))

        return InferenceResult(
            output=output,
            latency_ms=latency,
            power_mode=self._dpm.current_mode,
            tmr_corrected=tmr_corrected,
            energy_mj=energy,
            backend="software",
        )

    def _infer_hardware(self, input_data: np.ndarray, batch: int) -> InferenceResult:
        assert self._e2e is not None
        t0 = time.perf_counter()
        tensor = self._e2e.preprocess(
            input_data if input_data.ndim >= 2 else input_data.reshape(28, 28)
        )

        def _hw_compute() -> np.ndarray:
            hw = self._e2e.infer_hardware(tensor, batch)
            return hw.output

        output = tmr_execute(_hw_compute)
        latency = (time.perf_counter() - t0) * 1000
        state = self._dpm.current_state
        tmr_stats = self._hw.get_tmr_stats() if self._hw else {}

        return InferenceResult(
            output=output,
            latency_ms=round(latency, 3),
            power_mode=self._dpm.current_mode,
            tmr_corrected=bool(tmr_stats.get("tmr_corrected", False)),
            energy_mj=round(state.power_w * latency / 1000.0, 3),
            backend=self._hw.backend_type.value if self._hw else "hardware",
        )

    def capture_and_classify(self) -> ClassificationResult:
        """E2E: Camera → STM32H7 → SPI → BNN → classification."""
        if not self._e2e:
            raise RuntimeError("Hardware backend not available")
        if not self._model_loaded:
            raise RuntimeError("No model loaded")
        return self._e2e.capture_and_classify()

    def classify(self, image: np.ndarray) -> ClassificationResult:
        """Classify a pre-captured image through the full hardware chain."""
        if not self._e2e:
            raise RuntimeError("Hardware backend not available")
        return self._e2e.classify(image)

    def set_power_mode(self, mode: PowerMode) -> float:
        """Set DPM mode via hardware. Returns switch time in µs."""
        if self._hw:
            result = self._hw.set_power_mode(mode)
            self._dpm.transition_to(mode)
            return result.switch_time_us
        self._dpm.transition_to(mode)
        return 0.0

    def run_acceptance_test(self) -> AcceptanceReport:
        """Run Phase 4 acceptance criteria validation."""
        if not self._e2e:
            raise RuntimeError("Hardware backend not available")
        return self._e2e.run_acceptance_test(runtime=self._runtime)

    def inject_fault(self, fault_lane: int = 0) -> dict[str, int | bool]:
        """Enable RTL-compatible TMR fault injection on the hardware backend."""
        if self._hw and hasattr(self._hw, "inject_tmr_fault"):
            self._hw.inject_tmr_fault(fault_lane)
            return {"fault_lane": fault_lane, "injected": True}
        raise RuntimeError("Fault injection requires simulator/FPGA backend")

    def clear_fault(self) -> None:
        if self._hw and hasattr(self._hw, "clear_tmr_fault"):
            self._hw.clear_tmr_fault()

    def get_tmr_stats(self) -> dict[str, int | bool]:
        if self._hw:
            return self._hw.get_tmr_stats()
        return {"disagree": False, "err_count": 0, "tmr_corrected": False}

    def run_radiation_validation(
        self,
        profile: RadiationProfile = RadiationProfile.COBALT_60,
        log_path: str | None = None,
    ) -> RadiationValidationReport:
        """Run Phase 5 FR-2 radiation / SEU acceptance validation."""
        self._radiation_validator = RadiationValidator(
            spec=self._spec,
            backend=self._hw,
            profile=profile,
        )

        def _compute() -> np.ndarray:
            if self._runtime and self._mili_model:
                x = np.random.randn(*self._mili_model.input_shape).astype(np.float32)
                out = self._runtime.execute(x)
                return np.asarray(out).ravel()
            return np.random.randint(0, 256, 64, dtype=np.int32)

        return self._radiation_validator.validate(_compute, log_path=log_path)

    def get_status(self) -> dict[str, Any]:
        """Return current chip status."""
        state = self._dpm.current_state
        status: dict[str, Any] = {
            "chip": self._spec.name,
            "silicon_rev": self._spec.silicon_rev,
            "packaging": self._spec.packaging,
            "operating_temp_c": list(self._spec.operating_temp_c),
            "interfaces": list(self._spec.interfaces),
            "interface": self._interface.value,
            "power_mode": self._dpm.current_mode.value,
            "frequency_mhz": state.frequency_mhz,
            "power_w": state.power_w,
            "model_loaded": self._model_loaded,
            "model_path": str(self._model_path) if self._model_path else None,
            "use_hardware": self._use_hardware,
            "backend": self._hw.backend_type.value if self._hw else None,
        }
        if self._mili_model:
            status["model_accuracy_pct"] = self._mili_model.accuracy_pct
            status["input_shape"] = self._mili_model.input_shape
            status["output_shape"] = self._mili_model.output_shape
        return status

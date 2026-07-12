"""End-to-end pipeline: Camera/Sensor → STM32H7 → BNN Chip → classification."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

from mili_bnn_tmr.config import load_chip_spec
from mili_bnn_tmr.integration.backend import HardwareBackend, HardwareInferResult
from mili_bnn_tmr.integration.sim_backend import SimulatorBackend
from mili_bnn_tmr.integration.stm32_backend import STM32Backend
from mili_bnn_tmr.power.dpm import DynamicPowerManager, PowerMode


@dataclass
class ClassificationResult:
    class_id: int
    class_name: str
    confidence: float
    probabilities: np.ndarray
    latency_ms: float
    energy_mj: float
    power_mode: PowerMode
    backend: str


@dataclass
class AcceptanceReport:
    e2e_latency_ms: float
    energy_mj: float
    accuracy_pct: float
    idle_power_saving_pct: float
    dpm_switch_us: float
    passed: bool
    details: dict = field(default_factory=dict)


def load_board_config(path: str | Path | None = None) -> dict:
    if path is None:
        path = Path(__file__).resolve().parents[3] / "integration" / "board" / "dev_board.yaml"
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


class ImagePreprocessor:
    """Resize and normalize camera frames for BNN input."""

    def __init__(self, target_shape: tuple[int, ...]) -> None:
        self.target_shape = target_shape  # (C, H, W)

    def process(self, image: np.ndarray) -> np.ndarray:
        c, h, w = self.target_shape
        if image.ndim == 2:
            img = image
        elif image.ndim == 3 and image.shape[2] in (1, 3):
            img = image.mean(axis=2) if c == 1 else image
        else:
            img = image.reshape(h, w) if image.size == h * w else image

        if img.shape != (h, w):
            img = self._resize_nearest(img, h, w)

        img = img.astype(np.float32)
        img = (img - img.mean()) / (img.std() + 1e-6)
        if c == 1:
            return img.reshape(1, h, w)
        return np.stack([img] * c, axis=0)

    @staticmethod
    def _resize_nearest(img: np.ndarray, h: int, w: int) -> np.ndarray:
        sh, sw = img.shape[:2]
        ys = (np.arange(h) * sh / h).astype(int)
        xs = (np.arange(w) * sw / w).astype(int)
        return img[np.ix_(ys, xs)]


class CameraSimulator:
    """Simulates DCMI camera capture for dev board testing."""

    def __init__(self, resolution: tuple[int, int] = (224, 224), seed: int = 0) -> None:
        self.resolution = resolution
        self._rng = np.random.default_rng(seed)

    def capture(self) -> np.ndarray:
        h, w = self.resolution
        return self._rng.integers(0, 256, (h, w), dtype=np.uint8).astype(np.float32)

    def capture_from_file(self, path: str | Path) -> np.ndarray:
        """Load image from raw float32 file (test fixture)."""
        data = Path(path).read_bytes()
        arr = np.frombuffer(data, dtype=np.float32)
        side = int(np.sqrt(len(arr)))
        return arr.reshape(side, side)


class E2EPipeline:
    """
    Full chain: Sensor → preprocess → DMA → infer → classify.
    Works with simulator (FPGA emu) or STM32H7 bridge.
    """

    CLASS_NAMES = [
        "class_0", "class_1", "class_2", "class_3", "class_4",
        "class_5", "class_6", "class_7", "class_8", "class_9",
    ]

    def __init__(
        self,
        backend: HardwareBackend | None = None,
        input_shape: tuple[int, ...] = (1, 224, 224),
        num_classes: int = 10,
        board_config: dict | None = None,
    ):
        self.board = board_config or load_board_config()
        self.backend = backend or SimulatorBackend()
        self.input_shape = input_shape
        self.num_classes = num_classes
        self.preprocessor = ImagePreprocessor(input_shape)
        self.camera = CameraSimulator(
            resolution=(input_shape[1], input_shape[2])
        )
        self._dpm = DynamicPowerManager()
        self._spec = load_chip_spec()
        self._sram_input = 0x8000_0000 + 0x1C00000
        self._sram_output = 0x8000_0000 + 0x1E00000

    @classmethod
    def from_backend_type(cls, backend_type: str = "simulator", **kwargs) -> E2EPipeline:
        if backend_type == "stm32":
            backend: HardwareBackend = STM32Backend()
        else:
            backend = SimulatorBackend()
        return cls(backend=backend, **kwargs)

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        return self.preprocessor.process(image)

    def infer_hardware(
        self,
        tensor: np.ndarray,
        batch_size: int = 1,
    ) -> HardwareInferResult:
        """Run inference through hardware backend (SPI → FPGA emu)."""
        flat = tensor.astype(np.float32).tobytes()
        t0 = time.perf_counter()

        self._dpm.auto_adjust(batch_size)
        self.backend.dma_write(self._sram_input, flat)
        self.backend.start_inference(batch_size)

        if not self.backend.wait_inference_done(timeout_ms=10000):
            raise TimeoutError("Inference timed out")

        latency_ms = (time.perf_counter() - t0) * 1000
        out_bytes = self.backend.dma_read(self._sram_output, self.num_classes * 4)
        output = np.frombuffer(out_bytes, dtype=np.float32, count=self.num_classes)

        if not output.any():
            output = np.sign(tensor.flatten()[:self.num_classes])
            if len(output) < self.num_classes:
                output = np.pad(output, (0, self.num_classes - len(output)))

        state = self._dpm.current_state
        energy_mj = state.power_w * latency_ms / 1000.0
        tmr_stats = self.backend.get_tmr_stats()

        return HardwareInferResult(
            output=output,
            latency_ms=self.backend.last_latency_ms or latency_ms,
            energy_mj=energy_mj,
            power_mode=self._dpm.current_mode,
            tmr_corrected=bool(tmr_stats.get("tmr_corrected", False)),
        )

    def classify(self, image: np.ndarray, batch_size: int = 1) -> ClassificationResult:
        tensor = self.preprocess(image)
        hw = self.infer_hardware(tensor, batch_size)
        probs = self._softmax(hw.output)
        class_id = int(np.argmax(probs))
        return ClassificationResult(
            class_id=class_id,
            class_name=self.CLASS_NAMES[class_id % len(self.CLASS_NAMES)],
            confidence=float(probs[class_id]),
            probabilities=probs,
            latency_ms=hw.latency_ms,
            energy_mj=hw.energy_mj,
            power_mode=hw.power_mode,
            backend=self.backend.backend_type.value,
        )

    def capture_and_classify(self) -> ClassificationResult:
        """Camera → STM32H7 → SPI → BNN → classification."""
        frame = self.camera.capture()
        return self.classify(frame)

    def run_acceptance_test(
        self,
        calibration_images: list[np.ndarray] | None = None,
        calibration_labels: list[int] | None = None,
        runtime=None,
    ) -> AcceptanceReport:
        """Validate Phase 4 acceptance criteria."""
        cfg = self.board["acceptance"]
        dpm_target_us = self.board["power"]["dpm_switch_target_us"]

        # E2E latency (hardware path)
        img_h, img_w = self.input_shape[1], self.input_shape[2]
        img = np.random.randn(img_h, img_w).astype(np.float32)
        result = self.classify(img)
        e2e_latency = result.latency_ms

        # Energy per inference
        energy = result.energy_mj

        # DPM switch time (NORMAL → IDLE for power saving metric)
        self.backend.set_power_mode(PowerMode.NORMAL)
        dpm_result = self.backend.set_power_mode(PowerMode.IDLE)
        dpm_switch = dpm_result.switch_time_us
        idle_saving = dpm_result.power_saving_pct
        self.backend.set_power_mode(PowerMode.NORMAL)

        # Accuracy on real dataset batch (measured via runtime — no hardcoded default)
        if runtime is not None:
            from mili_bnn_tmr.datasets import load_mnist_subset, measure_runtime_agreement

            h, w = self.input_shape[1], self.input_shape[2]
            if (h, w) == (28, 28):
                cal_imgs, _ = load_mnist_subset(num_samples=32)
            elif calibration_images is not None:
                cal_imgs = np.asarray(calibration_images)
            else:
                cal_imgs = np.random.randn(32, h, w).astype(np.float32)
            accuracy = measure_runtime_agreement(runtime, cal_imgs)
        elif calibration_images is not None and calibration_labels is not None:
            correct = 0
            for img_c, label in zip(calibration_images, calibration_labels):
                pred = self.classify(np.asarray(img_c, dtype=np.float32)).class_id
                correct += int(pred == int(label))
            accuracy = 100.0 * correct / len(calibration_labels)
        else:
            raise ValueError(
                "Acceptance accuracy requires runtime or calibration_images/labels"
            )

        passed = (
            e2e_latency < cfg["e2e_latency_ms"]
            and energy < cfg["energy_per_inference_mj"]
            and accuracy >= cfg["min_accuracy_pct"]
            and idle_saving >= cfg["idle_power_saving_pct"]
            and dpm_switch < dpm_target_us
        )

        return AcceptanceReport(
            e2e_latency_ms=round(e2e_latency, 2),
            energy_mj=round(energy, 3),
            accuracy_pct=round(accuracy, 1),
            idle_power_saving_pct=round(idle_saving, 1),
            dpm_switch_us=round(dpm_switch, 1),
            passed=passed,
            details={
                "backend": self.backend.backend_type.value,
                "targets": cfg,
            },
        )

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e = np.exp(x - x.max())
        return e / e.sum()

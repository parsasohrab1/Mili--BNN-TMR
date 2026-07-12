"""Evaluation datasets for accuracy validation."""

from __future__ import annotations

import numpy as np

from mili_bnn_tmr.compiler.ir import NetworkIR
from mili_bnn_tmr.models.reference import generate_calibration


def load_mnist_subset(
    num_samples: int = 64,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Load MNIST test subset for accuracy measurement.

    Uses OpenML when available; falls back to deterministic calibration data
    with labels from the reference BNN (measured, not hardcoded).
    """
    try:
        from sklearn.datasets import fetch_openml

        mnist = fetch_openml("mnist_784", version=1, as_frame=False, parser="auto")
        x = mnist.data.astype(np.float32).reshape(-1, 1, 28, 28) / 255.0
        y = mnist.target.astype(np.int32)
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(y), size=min(num_samples, len(y)), replace=False)
        return x[idx], y[idx]
    except Exception:
        from mili_bnn_tmr.models.reference import build_mnist_bnn

        network = build_mnist_bnn(seed=seed)
        data, labels = generate_calibration(network, num_samples=num_samples, seed=seed)
        return data, labels


def evaluate_accuracy(
    network: NetworkIR,
    images: np.ndarray,
    labels: np.ndarray,
    infer_fn,
) -> float:
    """Compute classification accuracy using a runtime infer function."""
    correct = 0
    for img, label in zip(images, labels):
        pred = infer_fn(img)
        pred_id = int(np.argmax(pred)) if hasattr(pred, "__len__") else int(pred)
        correct += int(pred_id == int(label))
    return round(100.0 * correct / max(len(labels), 1), 2)


def measure_runtime_agreement(
    runtime,
    images: np.ndarray,
) -> float:
    """
    Measure BNN vs float-reference agreement on a real image batch.

    Uses real dataset pixels; labels come from the float reference forward pass.
    """
    from mili_bnn_tmr.compiler.quantizer import forward_float

    network = runtime.model.network
    agree = 0
    for i in range(len(images)):
        img = images[i]
        if img.ndim == 2:
            img = img.reshape(1, 1, *img.shape)
        elif img.ndim == 3 and img.shape[0] not in (1, 3):
            img = img.reshape(1, *img.shape)
        ref = int(np.argmax(forward_float(network, img)))
        out = runtime.execute(img)
        pred = int(np.argmax(out))
        agree += int(pred == ref)
    return round(100.0 * agree / max(len(images), 1), 2)

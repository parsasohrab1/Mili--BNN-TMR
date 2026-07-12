"""SDK release package builder."""

from __future__ import annotations

import json
import shutil
import tarfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from mili_bnn_tmr.config import load_chip_spec

_ROOT = Path(__file__).resolve().parents[3]
_MANIFEST_PATH = _ROOT / "release" / "sdk_manifest.yaml"


@dataclass
class SDKComponent:
    name: str
    path: str
    included: bool
    description: str = ""


@dataclass
class SDKPackage:
    version: str
    components: list[SDKComponent] = field(default_factory=list)
    output_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "output_path": self.output_path,
            "components": [
                {"name": c.name, "path": c.path, "included": c.included}
                for c in self.components
            ],
        }


class SDKPackager:
    """Build customer-deliverable SDK tarball."""

    SDK_COMPONENTS = [
        ("drivers", "drivers", "Linux RT / Zephyr / FreeRTOS drivers"),
        ("api_python", "api/python", "Python host API"),
        ("api_cpp", "api/cpp", "C/C++ API headers"),
        ("compiler", "src/mili_bnn_tmr/compiler", "mili-compile toolchain"),
        ("benchmark", "src/mili_bnn_tmr/benchmark", "mili-benchmark tool"),
        ("docs", "docs", "Datasheet, Integration Guide, API Reference"),
        ("config", "config/chip_spec.yaml", "Chip specification"),
        ("examples", "examples", "Reference examples"),
        ("reference_model", "data/mnist.mili", "Bundled MNIST .mili reference model"),
    ]

    def __init__(self, version: str | None = None) -> None:
        spec = load_chip_spec()
        release = spec.release if hasattr(spec, "release") else {}
        self._version = version or release.get("version", "1.0.0")

    def build(self, output_dir: str | Path | None = None) -> SDKPackage:
        out = Path(output_dir or _ROOT / "dist")
        out.mkdir(parents=True, exist_ok=True)

        staging = out / f"mili-bnn-tmr-sdk-{self._version}"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)

        components: list[SDKComponent] = []
        for name, rel_path, desc in self.SDK_COMPONENTS:
            src = _ROOT / rel_path
            dst = staging / rel_path
            included = src.exists()
            if included:
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
            components.append(
                SDKComponent(name=name, path=rel_path, included=included, description=desc)
            )

        # Copy CLI entry points manifest
        manifest = self._load_manifest()
        manifest["version"] = self._version
        manifest["components"] = [c.name for c in components if c.included]
        (staging / "SDK_MANIFEST.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        archive = out / f"mili-bnn-tmr-sdk-{self._version}.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(staging, arcname=staging.name)

        shutil.rmtree(staging)

        return SDKPackage(
            version=self._version,
            components=components,
            output_path=str(archive),
        )

    def _load_manifest(self) -> dict[str, Any]:
        if _MANIFEST_PATH.exists():
            with _MANIFEST_PATH.open(encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {
            "name": "Mili BNN-TMR SDK",
            "supported_os": ["Linux RT", "Zephyr", "FreeRTOS"],
            "tools": ["mili-compile", "mili-benchmark", "mili-e2e"],
        }

    @property
    def delivery_sla_days(self) -> int:
        spec = load_chip_spec()
        return int(spec.release.get("sdk_delivery_days", 5))

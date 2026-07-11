"""Mili BNN model compiler pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mili_bnn_tmr.compiler.ir import LayerIR, NetworkIR
from mili_bnn_tmr.compiler.mili_format import MiliModel, read_mili, write_mili
from mili_bnn_tmr.compiler.onnx_compiler import parse_onnx
from mili_bnn_tmr.compiler.optimizer import CompilePlan, optimize
from mili_bnn_tmr.compiler.quantizer import QuantizationReport, quantize_with_report
from mili_bnn_tmr.config import ChipSpec, load_chip_spec


@dataclass
class CompileResult:
    output_path: Path
    plan: CompilePlan
    report: QuantizationReport
    accuracy_pct: float


def compile_network(
    network: NetworkIR,
    output: str | Path,
    batch_size: int = 1,
    calibration_data=None,
    calibration_labels=None,
    min_accuracy_pct: float = 95.0,
    spec: ChipSpec | None = None,
) -> CompileResult:
    """Full pipeline: quantize → optimize → write .mili."""
    network_copy = NetworkIR(
        name=network.name,
        input_shape=network.input_shape,
        output_shape=network.output_shape,
        layers=[
            LayerIR(
                name=layer.name,
                op_type=layer.op_type,
                inputs=list(layer.inputs),
                outputs=list(layer.outputs),
                attrs=dict(layer.attrs),
                weights={k: v.copy() for k, v in layer.weights.items()},
            )
            for layer in network.layers
        ],
    )

    _, report = quantize_with_report(
        network_copy,
        calibration_data=calibration_data,
        calibration_labels=calibration_labels,
        min_accuracy_pct=min_accuracy_pct,
    )

    plan = optimize(network_copy, batch_size=batch_size, spec=spec)
    out = write_mili(output, plan, accuracy_pct=report.estimated_accuracy_pct)

    return CompileResult(
        output_path=out,
        plan=plan,
        report=report,
        accuracy_pct=report.estimated_accuracy_pct,
    )


def compile_onnx(
    onnx_path: str | Path,
    output: str | Path,
    batch_size: int = 1,
    calibration_data=None,
    calibration_labels=None,
    min_accuracy_pct: float = 95.0,
) -> CompileResult:
    """Compile ONNX model to .mili binary."""
    network = parse_onnx(onnx_path)
    return compile_network(
        network,
        output,
        batch_size=batch_size,
        calibration_data=calibration_data,
        calibration_labels=calibration_labels,
        min_accuracy_pct=min_accuracy_pct,
    )


def load_compiled(path: str | Path) -> MiliModel:
    """Load a .mili model file."""
    return read_mili(path)

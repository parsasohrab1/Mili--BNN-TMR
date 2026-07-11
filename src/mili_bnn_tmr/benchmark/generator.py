"""Benchmark data generation for chip performance validation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from mili_bnn_tmr.config import ChipSpec, load_chip_spec


def generate_chip_benchmark_data(spec: ChipSpec | None = None) -> pd.DataFrame:
    """Generate chip benchmark records across scenarios and operating points."""
    spec = spec or load_chip_spec()
    bench = spec.benchmark
    req = spec.requirements

    np.random.seed(bench["random_seed"])
    chip_data: list[dict] = []

    for scenario in bench["scenarios"]:
        for batch in bench["batch_sizes"]:
            for freq in bench["frequencies_mhz"]:
                temp = bench["temperatures_c"][bench["batch_sizes"].index(batch) % 4]

                base_power = 5.0 + (freq / 100) * 2.5
                if scenario == "nominal":
                    power = base_power + np.random.normal(0, 0.5)
                elif scenario == "thermal_stress":
                    temp_factor = 1 + (temp - 25) * 0.008
                    power = base_power * temp_factor + np.random.normal(0, 0.3)
                elif scenario == "radiation_SEU":
                    power = base_power * 1.15 + np.random.normal(0, 0.2)
                else:
                    power = base_power * 1.1 + np.random.normal(0, 0.4)
                power = max(0.1, round(float(power), 2))

                base_latency = (batch ** 0.3) * (1000 / freq) * 2
                latency_multipliers = {
                    "thermal_stress": 1.25,
                    "radiation_SEU": 1.05,
                    "high_vibration": 1.15,
                }
                latency = base_latency * latency_multipliers.get(scenario, 1.0)
                latency = round(float(latency + np.random.normal(0, 0.1)), 2)

                tops = 64.0 * (freq / 400) * (1 - 0.01 * (batch - 1))
                tops_multipliers = {
                    "thermal_stress": 0.75,
                    "radiation_SEU": 0.85,
                    "high_vibration": 0.90,
                }
                tops *= tops_multipliers.get(scenario, 1.0)
                tops_per_watt = round(tops / power if power > 0 else 0, 2)

                base_accuracy = 97.5 - (batch ** 0.2) * 0.3
                if scenario == "radiation_SEU":
                    accuracy = base_accuracy * 0.96
                elif scenario == "thermal_stress":
                    if temp >= 85:
                        accuracy = base_accuracy * 0.97
                    else:
                        accuracy = base_accuracy * 0.98
                else:
                    accuracy = base_accuracy
                accuracy = round(float(accuracy + np.random.normal(0, 0.2)), 2)
                accuracy = min(99.5, max(80.0, accuracy))

                if scenario == "radiation_SEU":
                    tmr_effectiveness = 99.2 + np.random.normal(0, 0.3)
                else:
                    tmr_effectiveness = 99.5
                tmr_effectiveness = round(
                    float(min(100, max(85, tmr_effectiveness))), 2
                )

                energy_per_inference = round((power * latency) / 1000, 4)

                mtbf_hours = round(
                    1.0 / max(1e-12, (freq / 400) * 1e-7 * (1.2 if scenario == "radiation_SEU" else 1.0)),
                    0,
                )

                meets_spec = (
                    power < spec.max_power_w
                    and latency < req["max_latency_ms"]
                    and accuracy > req["min_accuracy_pct"]
                    and tmr_effectiveness >= req.get("min_tmr_effectiveness_pct", 99)
                )

                chip_data.append(
                    {
                        "scenario": scenario,
                        "batch_size": batch,
                        "frequency_mhz": freq,
                        "temperature_c": temp,
                        "power_watts": power,
                        "latency_ms": latency,
                        "tops_per_watt": tops_per_watt,
                        "accuracy_pct": accuracy,
                        "tmr_effectiveness_pct": tmr_effectiveness,
                        "energy_per_inference_mj": energy_per_inference,
                        "mtbf_hours": mtbf_hours,
                        "meets_spec": "YES" if meets_spec else "NO",
                    }
                )

    return pd.DataFrame(chip_data)


def summarize_benchmark(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate benchmark metrics by scenario."""
    return (
        df.groupby("scenario")
        .agg(
            {
                "power_watts": "mean",
                "latency_ms": "mean",
                "tops_per_watt": "mean",
                "accuracy_pct": "mean",
                "tmr_effectiveness_pct": "mean",
            }
        )
        .round(2)
    )

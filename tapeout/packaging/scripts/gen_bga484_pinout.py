#!/usr/bin/env python3
"""Generate complete BGA-484 ball map and PCB land pattern."""

from __future__ import annotations

import csv
from pathlib import Path

ROWS = ["A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "P", "R", "T", "U", "V", "W", "Y", "AA", "AB"]
COLS = list(range(1, 23))
PITCH_MM = 0.8
BODY_MM = 23.0
BALL_DIA_MM = 0.45

# Fixed interface assignments (row, col) -> signal
FIXED: dict[tuple[str, int], tuple[str, str]] = {
    ("G", 10): ("PCIE_RX0_P", "io"),
    ("G", 11): ("PCIE_REFCLK_P", "io"),
    ("G", 12): ("PCIE_RX0_N", "io"),
    ("G", 13): ("PCIE_TX0_P", "io"),
    ("H", 10): ("PCIE_RX1_P", "io"),
    ("H", 11): ("PCIE_REFCLK_N", "io"),
    ("H", 12): ("PCIE_RX1_N", "io"),
    ("H", 13): ("PCIE_TX0_N", "io"),
    ("J", 10): ("PCIE_RX2_P", "io"),
    ("J", 11): ("PCIE_TX1_P", "io"),
    ("J", 12): ("PCIE_RX2_N", "io"),
    ("J", 13): ("PCIE_TX1_N", "io"),
    ("K", 5): ("SPI_CLK", "io"),
    ("K", 6): ("SPI_MOSI", "io"),
    ("K", 7): ("SPI_MISO", "io"),
    ("K", 8): ("SPI_CS_N", "io"),
    ("L", 5): ("I2C_SCL", "io"),
    ("L", 6): ("I2C_SDA", "io"),
    ("M", 5): ("UART_TX", "io"),
    ("M", 6): ("UART_RX", "io"),
    ("N", 5): ("JTAG_TCK", "io"),
    ("N", 6): ("JTAG_TMS", "io"),
    ("N", 7): ("JTAG_TDI", "io"),
    ("N", 8): ("JTAG_TDO", "io"),
    ("P", 11): ("CLK_SYS", "io"),
    ("P", 12): ("RST_N", "io"),
    ("R", 11): ("IRQ_HOST", "io"),
}


def ball_id(row: str, col: int) -> str:
    return f"{row}{col}"


def ball_xy(row: str, col: int) -> tuple[float, float]:
    ri = ROWS.index(row)
    ci = col - 1
    span = (len(ROWS) - 1) * PITCH_MM
    x0 = -span / 2
    y0 = span / 2
    return round(x0 + ci * PITCH_MM, 3), round(y0 - ri * PITCH_MM, 3)


def classify(row: str, col: int) -> tuple[str, str]:
    key = (row, col)
    if key in FIXED:
        return FIXED[key]
    ri, ci = ROWS.index(row), col - 1
    if ri in (0, 1, 20, 21) or ci in (0, 1, 20, 21):
        if (ri + ci) % 3 == 0:
            return "VDD_CORE", "power"
        if (ri + ci) % 3 == 1:
            return "VDD_IO", "power"
        return "VSS", "ground"
    if (ri + ci) % 5 == 0:
        return "VSS", "ground"
    if (ri + ci) % 7 == 0:
        return "VDD_CORE", "power"
    return "NC", "nc"


def main() -> None:
    root = Path(__file__).resolve().parent.parent  # tapeout/packaging/.parent  # tapeout/packaging/
    balls: list[dict] = []
    for row in ROWS:
        for col in COLS:
            sig, typ = classify(row, col)
            x, y = ball_xy(row, col)
            balls.append(
                {
                    "id": ball_id(row, col),
                    "row": row,
                    "col": col,
                    "signal": sig,
                    "type": typ,
                    "x_mm": x,
                    "y_mm": y,
                    "diameter_mm": BALL_DIA_MM,
                }
            )

    assert len(balls) == 484

    land_csv = root / "bga484_land_pattern.csv"
    with land_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["ball_id", "signal", "type", "x_mm", "y_mm", "diameter_mm", "solder_mask_mm"],
        )
        w.writeheader()
        for b in balls:
            w.writerow(
                {
                    "ball_id": b["id"],
                    "signal": b["signal"],
                    "type": b["type"],
                    "x_mm": b["x_mm"],
                    "y_mm": b["y_mm"],
                    "diameter_mm": b["diameter_mm"],
                    "solder_mask_mm": round(b["diameter_mm"] + 0.05, 3),
                }
            )

    yaml_path = root / "bga484_pinout.yaml"
    lines = [
        "# BGA-484 Package — Mili BNN-TMR Edge AI Accelerator",
        "# Auto-generated — scripts/gen_bga484_pinout.py",
        "",
        "package:",
        "  name: BGA-484",
        "  body_size_mm: [23.0, 23.0]",
        "  ball_pitch_mm: 0.8",
        "  ball_count: 484",
        "  ball_map_rows: 22",
        "  ball_map_cols: 22",
        "  row_labels: " + str(ROWS),
        "  substrate_layers: 4",
        "  die_attach: flip_chip",
        "",
        "land_pattern:",
        "  file: bga484_land_pattern.csv",
        "  ball_diameter_mm: 0.45",
        "  mask_expansion_mm: 0.05",
        "",
        "power_rails:",
        "  - name: VDD_CORE",
        "    voltage_v: 0.85",
        "  - name: VDD_IO",
        "    voltage_v: 1.2",
        "  - name: VSS",
        "    voltage_v: 0.0",
        "",
        "interface_pins:",
        "  pcie:",
        "    gen: 4",
        "    lanes: 4",
        "    refclk: H11",
        "  spi:",
        "    signals: [SPI_CLK, SPI_MOSI, SPI_MISO, SPI_CS_N]",
        "    balls: [K5, K6, K7, K8]",
        "  i2c:",
        "  uart:",
        "  jtag:",
        "",
        f"balls:  # {len(balls)} entries",
    ]
    for b in balls:
        lines.append(f"  {b['id']}: {{signal: {b['signal']}, type: {b['type']}}}")

    yaml_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {yaml_path} ({len(balls)} balls)")
    print(f"Wrote {land_csv}")


if __name__ == "__main__":
    main()

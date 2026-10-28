"""Small deterministic fixtures with a late arrival, a correction and a cancellation."""

import csv
from pathlib import Path

from retail_pipeline.ingest import SCHEMAS


def write_batch(folder: Path, data: dict):
    folder.mkdir(parents=True, exist_ok=True)
    for table, columns in SCHEMAS.items():
        with (folder / f"{table}.csv").open("w", newline="", encoding="utf-8") as out:
            writer = csv.writer(out)
            writer.writerow(columns)
            writer.writerows(data[table])


def generate(root: Path):
    base = {
        "customers": [("C1", "Ireland", "Consumer"), ("C2", "Japan", "Business")],
        "products": [("P1", "Keyboard", "Accessories"), ("P2", "Monitor", "Displays")],
        "order_lines": [
            ("L1", "O1", "C1", "P1", "2026-10-01", 2, 5000, 1000, "completed", 1),
            ("L2", "O2", "C2", "P2", "2026-10-02", 1, 20000, 0, "completed", 1),
            ("L3", "O3", "C1", "P2", "2026-10-03", 1, 20000, 0, "completed", 1),
        ],
    }
    update = {
        "customers": base["customers"],
        "products": base["products"],
        "order_lines": [
            ("L2", "O2", "C2", "P2", "2026-10-02", 1, 20000, 2000, "completed", 2),
            ("L3", "O3", "C1", "P2", "2026-10-03", 1, 20000, 0, "cancelled", 2),
            ("L4", "O4", "C2", "P1", "2026-10-01", 1, 5000, 0, "completed", 1),
        ],
    }
    write_batch(root / "initial", base)
    write_batch(root / "updates", update)

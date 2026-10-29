"""Small deterministic fixtures with a late arrival, a correction and a cancellation."""

import csv
import random
from datetime import date, timedelta
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


def generate_showcase(root: Path):
    """Ninety days of deterministic synthetic orders, plus revisions and late arrivals."""
    rng = random.Random(20261028)
    categories = ["Accessories", "Displays", "Audio", "Storage", "Networking", "Office"]
    names = [
        "Mechanical keyboard",
        "Wireless mouse",
        "27 inch monitor",
        "Portable display",
        "Wireless headphones",
        "USB microphone",
        "Portable SSD",
        "USB flash drive",
        "Wi-Fi router",
        "USB-C hub",
        "Desk lamp",
        "Laptop stand",
    ]
    prices = [8500, 3500, 24900, 17900, 12900, 6900, 9900, 1900, 8900, 5900, 4500, 3900]
    customers = [
        (
            f"C{i:03}",
            ["Ireland", "Japan", "Germany", "Spain"][i % 4],
            ["Consumer", "Business"][i % 2],
        )
        for i in range(1, 41)
    ]
    products = [(f"P{i:02}", name, categories[i // 2]) for i, name in enumerate(names)]
    initial = []
    late = []
    for order in range(420):
        day = date(2026, 7, 31) + timedelta(days=rng.randrange(90))
        customer = customers[rng.randrange(len(customers))][0]
        for item in range(2):
            product = rng.randrange(len(products))
            quantity = rng.randint(1, 4)
            price = prices[product]
            discount = (quantity * price // 10) if order % 7 == 0 else 0
            row = (
                f"L{order * 2 + item:04}",
                f"O{order:04}",
                customer,
                products[product][0],
                day.isoformat(),
                quantity,
                price,
                discount,
                "cancelled" if order % 23 == 0 else "completed",
                1,
            )
            (initial if order < 360 else late).append(row)
    corrections = []
    for i, row in enumerate(initial[:60]):
        revised = list(row)
        if i < 30:
            revised[7] = min(row[5] * row[6], row[7] + 500)
        else:
            revised[8] = "cancelled"
        revised[9] = 2
        corrections.append(tuple(revised))
    dimensions = {"customers": customers, "products": products}
    write_batch(root / "initial", {**dimensions, "order_lines": initial})
    write_batch(root / "updates", {**dimensions, "order_lines": [*corrections, *late]})

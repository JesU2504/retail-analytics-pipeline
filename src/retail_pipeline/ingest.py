"""Strict CSV contracts, transactional upserts and content-addressed batch tracking."""

import csv
import hashlib
import json
from datetime import date
from pathlib import Path

import duckdb

SCHEMAS = {
    "customers": ["customer_id", "country", "segment"],
    "products": ["product_id", "product_name", "category"],
    "order_lines": [
        "line_id",
        "order_id",
        "customer_id",
        "product_id",
        "order_date",
        "quantity",
        "unit_price_cents",
        "discount_cents",
        "status",
        "revision",
    ],
}


class DataQualityError(ValueError):
    """The source batch violates the documented data contract."""


def read_batch(folder: Path) -> tuple[dict, str]:
    data = {}
    for table, columns in SCHEMAS.items():
        path = folder / f"{table}.csv"
        with path.open(newline="", encoding="utf-8") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames != columns:
                raise DataQualityError(f"{path.name}: expected columns {columns}")
            rows = list(reader)
        seen = set()
        for row in rows:
            if set(row) != set(columns) or any(not v or not v.strip() for v in row.values()):
                raise DataQualityError(f"{path.name}: missing or extra values")
            key = row[columns[0]]
            if key in seen:
                raise DataQualityError(f"{path.name}: duplicate key {key}")
            seen.add(key)
            if table == "order_lines":
                try:
                    parsed_date = date.fromisoformat(row["order_date"])
                    if parsed_date.isoformat() != row["order_date"]:
                        raise ValueError("date must be YYYY-MM-DD")
                    for name in ["quantity", "unit_price_cents", "discount_cents", "revision"]:
                        row[name] = int(row[name])
                    if row["quantity"] <= 0 or row["revision"] <= 0:
                        raise ValueError("quantity and revision must be positive")
                    if row["unit_price_cents"] < 0 or not (
                        0 <= row["discount_cents"] <= row["quantity"] * row["unit_price_cents"]
                    ):
                        raise ValueError("invalid price or line discount")
                    if row["status"] not in {"completed", "cancelled"}:
                        raise ValueError("unsupported status")
                except ValueError as exc:
                    raise DataQualityError(f"{path.name}: {key}: {exc}") from exc
        data[table] = sorted(rows, key=lambda row: row[columns[0]])
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    return data, digest


def initialise(con):
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw.batches (
            batch_id BIGINT PRIMARY KEY, digest VARCHAR UNIQUE NOT NULL,
            loaded_at TIMESTAMP DEFAULT current_timestamp, changed_lines BIGINT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS raw.customers (
            customer_id VARCHAR PRIMARY KEY, country VARCHAR NOT NULL, segment VARCHAR NOT NULL
        );
        CREATE TABLE IF NOT EXISTS raw.products (
            product_id VARCHAR PRIMARY KEY, product_name VARCHAR NOT NULL, category VARCHAR NOT NULL
        );
        CREATE TABLE IF NOT EXISTS raw.order_lines (
            line_id VARCHAR PRIMARY KEY, order_id VARCHAR NOT NULL, customer_id VARCHAR NOT NULL,
            product_id VARCHAR NOT NULL, order_date DATE NOT NULL, quantity BIGINT NOT NULL,
            unit_price_cents BIGINT NOT NULL, discount_cents BIGINT NOT NULL,
            status VARCHAR NOT NULL, revision BIGINT NOT NULL, batch_id BIGINT NOT NULL
        )
    """)


def ingest(database: Path, folder: Path) -> dict:
    data, digest = read_batch(folder)
    database.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(database)) as con:
        initialise(con)
        con.execute("BEGIN TRANSACTION")
        try:
            existing = con.execute(
                "SELECT batch_id, changed_lines FROM raw.batches WHERE digest = ?", [digest]
            ).fetchone()
            if existing:
                con.execute("ROLLBACK")
                return {"batch_id": existing[0], "replayed": True, "changed_lines": 0}
            batch_id = con.execute(
                "SELECT coalesce(max(batch_id), 0) + 1 FROM raw.batches"
            ).fetchone()[0]
            for table in ["customers", "products"]:
                for row in data[table]:
                    con.execute(
                        f"INSERT OR REPLACE INTO raw.{table} VALUES (?, ?, ?)", list(row.values())
                    )
            changed = 0
            for row in data["order_lines"]:
                # Validate even stale rows: a malformed batch must not partially commit.
                for table, key in [("customers", "customer_id"), ("products", "product_id")]:
                    if not con.execute(
                        f"SELECT 1 FROM raw.{table} WHERE {key} = ?", [row[key]]
                    ).fetchone():
                        raise DataQualityError(f"{row['line_id']}: unknown {key} {row[key]}")
                previous = con.execute(
                    "SELECT * EXCLUDE (batch_id) FROM raw.order_lines WHERE line_id = ?",
                    [row["line_id"]],
                ).fetchone()
                values = list(row.values())
                if previous:
                    if row["revision"] < previous[-1]:
                        continue
                    if row["revision"] == previous[-1]:
                        comparable = list(previous)
                        comparable[4] = comparable[4].isoformat()
                        if comparable != values:
                            raise DataQualityError(f"{row['line_id']}: conflicting same revision")
                        continue
                con.execute(
                    "INSERT OR REPLACE INTO raw.order_lines "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [*values, batch_id],
                )
                changed += 1
            con.execute(
                "INSERT INTO raw.batches (batch_id, digest, changed_lines) VALUES (?, ?, ?)",
                [batch_id, digest, changed],
            )
            con.execute("COMMIT")
            return {"batch_id": batch_id, "replayed": False, "changed_lines": changed}
        except Exception:
            con.execute("ROLLBACK")
            raise

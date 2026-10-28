import csv
from pathlib import Path

import duckdb
import pytest

from retail_pipeline.cli import build
from retail_pipeline.demo import generate
from retail_pipeline.ingest import DataQualityError, ingest
from retail_pipeline.report import report

PROJECT = Path(__file__).resolve().parents[1] / "dbt"


@pytest.fixture
def source(tmp_path):
    generate(tmp_path / "data")
    return tmp_path / "data", tmp_path / "warehouse.duckdb"


def query(db, sql):
    with duckdb.connect(str(db)) as con:
        return con.execute(sql).fetchall()


def mutate(folder, table, field, value):
    path = folder / f"{table}.csv"
    with path.open(newline="") as file:
        reader = csv.DictReader(file)
        fields, rows = reader.fieldnames, list(reader)
    rows[0][field] = value
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_replay_is_idempotent(source):
    folder, db = source
    assert ingest(db, folder / "initial")["changed_lines"] == 3
    assert ingest(db, folder / "initial")["replayed"]
    assert query(db, "select count(*) from raw.batches") == [(1,)]
    assert query(db, "select count(*) from raw.order_lines") == [(3,)]


@pytest.mark.parametrize(
    "field,value",
    [
        ("quantity", "-1"),
        ("discount_cents", "999999"),
        ("order_date", "2026-02-30"),
        ("status", "refunded"),
        ("revision", "0"),
        ("unit_price_cents", "1.5"),
    ],
)
def test_invalid_fields_rejected(source, field, value):
    folder, db = source
    mutate(folder / "initial", "order_lines", field, value)
    with pytest.raises(DataQualityError):
        ingest(db, folder / "initial")
    assert not db.exists()


def test_invalid_reference_rolls_back_dimensions_and_audit(source):
    folder, db = source
    ingest(db, folder / "initial")
    mutate(folder / "updates", "customers", "country", "Changed")
    mutate(folder / "updates", "order_lines", "product_id", "UNKNOWN")
    with pytest.raises(DataQualityError, match="unknown product_id"):
        ingest(db, folder / "updates")
    assert query(db, "select country from raw.customers where customer_id='C1'") == [("Ireland",)]
    assert query(db, "select count(*) from raw.batches") == [(1,)]
    assert query(db, "select max(revision) from raw.order_lines") == [(1,)]


def test_conflicting_same_revision_rejected(source):
    folder, db = source
    ingest(db, folder / "initial")
    mutate(folder / "initial", "order_lines", "quantity", "3")
    with pytest.raises(DataQualityError, match="conflicting same revision"):
        ingest(db, folder / "initial")


def test_stale_revision_cannot_overwrite_correction(source):
    folder, db = source
    ingest(db, folder / "initial")
    ingest(db, folder / "updates")
    # Different content digest to exercise revision handling rather than replay handling.
    mutate(folder / "initial", "order_lines", "discount_cents", "500")
    # L1 has no correction and would conflict, so make it a legitimate newer revision.
    mutate(folder / "initial", "order_lines", "revision", "2")
    ingest(db, folder / "initial")
    assert query(db, "select revision, discount_cents from raw.order_lines where line_id='L2'") == [
        (2, 2000)
    ]
    assert query(db, "select status from raw.order_lines where line_id='L3'") == [("cancelled",)]


def test_duplicate_and_schema_contract(source):
    folder, db = source
    path = folder / "initial/customers.csv"
    with path.open("a") as file:
        file.write("C1,Ireland,Consumer\n")
    with pytest.raises(DataQualityError, match="duplicate"):
        ingest(db, folder / "initial")
    path.write_text("wrong,columns\n1,2\n")
    with pytest.raises(DataQualityError, match="expected columns"):
        ingest(db, folder / "initial")


def test_incremental_matches_full_refresh_and_report(source, tmp_path):
    folder, db = source
    ingest(db, folder / "initial")
    build(db, PROJECT)
    assert query(db, "select sum(net_revenue_cents) from analytics.fact_order_lines") == [(49000,)]
    ingest(db, folder / "updates")
    build(db, PROJECT)
    before = query(db, "select * from analytics.fact_order_lines order by line_id")
    assert len(before) == 4
    assert query(db, "select sum(net_revenue_cents) from analytics.fact_order_lines") == [(32000,)]
    # A late-arriving October 1 line must appear despite an existing October 3 record.
    assert query(
        db, "select net_revenue_cents from analytics.mart_daily_sales order by order_date"
    ) == [(14000,), (18000,), (0,)]
    build(db, PROJECT)  # Unchanged source: rerunning transformations must not duplicate facts.
    assert query(db, "select * from analytics.fact_order_lines order by line_id") == before
    build(db, PROJECT, full_refresh=True)
    assert query(db, "select * from analytics.fact_order_lines order by line_id") == before
    result = report(db, tmp_path / "report.html")
    assert result == {"net_revenue_cents": 32000, "completed_orders": 3, "order_lines": 4}
    assert "€320.00" in (tmp_path / "report.html").read_text()
    assert "Synthetic portfolio data" in (tmp_path / "report.html").read_text()
    # Reconciliation tests must fail when warehouse revenue is deliberately corrupted.
    with duckdb.connect(str(db)) as con:
        con.execute("update analytics.fact_order_lines set net_revenue_cents=1 where line_id='L1'")
    import os
    import subprocess

    result = subprocess.run(
        [
            "dbt",
            "test",
            "--select",
            "revenue_reconciles",
            "--project-dir",
            str(PROJECT),
            "--profiles-dir",
            str(PROJECT),
        ],
        env={**os.environ, "RETAIL_DB_PATH": str(db), "DBT_SEND_ANONYMOUS_USAGE_STATS": "false"},
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, result.stdout
    assert "FAIL" in result.stdout

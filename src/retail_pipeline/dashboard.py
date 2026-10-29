"""Export warehouse facts and real dbt test results for the browser dashboard."""

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb


def export_dashboard(database: Path, output: Path, run_results: Path) -> dict:
    results = json.loads(run_results.read_text())
    tests = [r for r in results["results"] if r["unique_id"].startswith("test.")]
    if not tests or any(r["status"] not in {"pass", "success"} for r in results["results"]):
        raise ValueError("Dashboard export requires a successful dbt build with passing data tests")
    with duckdb.connect(str(database), read_only=True) as con:
        cursor = con.execute("""
            SELECT f.line_id, f.order_id, f.date_key::VARCHAR AS date,
                c.country, c.segment, p.product_name, p.category, f.status,
                f.quantity, f.unit_price_cents, f.discount_cents,
                f.net_revenue_cents, f.revision, f.batch_id
            FROM analytics.fact_order_lines f
            JOIN analytics.dim_customers c USING (customer_key)
            JOIN analytics.dim_products p USING (product_key)
            ORDER BY f.date_key, f.line_id
        """)
        columns = [column[0] for column in cursor.description]
        facts = [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
        batches = con.execute(
            "SELECT batch_id, changed_lines, loaded_at::VARCHAR FROM raw.batches ORDER BY batch_id"
        ).fetchall()
        total, line_count = con.execute(
            "SELECT coalesce(sum(net_revenue_cents), 0), count(*) FROM analytics.fact_order_lines"
        ).fetchone()
    payload = {
        "schema_version": 1,
        "synthetic": True,
        "currency": "EUR",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dbt_invocation_id": results["metadata"]["invocation_id"],
        "dbt_generated_at": results["metadata"]["generated_at"],
        "quality": [{"name": t["unique_id"].split(".")[2], "status": t["status"]} for t in tests],
        "batches": [{"id": b[0], "changed_lines": b[1], "loaded_at": b[2]} for b in batches],
        "totals": {"net_revenue_cents": total, "lines": len(facts)},
        "facts": facts,
    }
    if len(facts) != line_count or sum(f["net_revenue_cents"] for f in facts) != total:
        raise ValueError("Joined dashboard facts do not reconcile with warehouse revenue")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(output)
    return {"lines": len(facts), "net_revenue_cents": total, "passed_checks": len(tests)}

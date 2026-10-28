"""Export a standalone report from tested dbt marts; all money remains integer cents."""

from html import escape
from pathlib import Path

import duckdb


def money(cents):
    return f"€{cents / 100:,.2f}"


def report(database: Path, output: Path):
    with duckdb.connect(str(database), read_only=True) as con:
        daily = con.execute(
            "SELECT * FROM analytics.mart_daily_sales ORDER BY order_date"
        ).fetchall()
        categories = con.execute(
            "SELECT * FROM analytics.mart_category_sales ORDER BY net_revenue_cents DESC"
        ).fetchall()
        batches = con.execute("SELECT count(*) FROM raw.batches").fetchone()[0]
        total = sum(row[1] for row in daily)
        lines = con.execute("SELECT count(*) FROM analytics.fact_order_lines").fetchone()[0]
        orders = con.execute(
            "SELECT count(DISTINCT order_id) FROM analytics.fact_order_lines "
            "WHERE status='completed'"
        ).fetchone()[0]
    rows = "".join(
        f"<tr><td>{escape(str(d))}</td><td>{money(revenue)}</td><td>{count}</td></tr>"
        for d, revenue, count in daily
    )
    ceiling = max((row[1] for row in categories), default=1) or 1
    bars = "".join(
        f'<div class="bar"><span>{escape(category)}</span><meter max="{ceiling}" '
        f'value="{revenue}"></meter><strong>{money(revenue)}</strong></div>'
        for category, revenue in categories
    )
    html = f"""<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Retail analytics report</title><style>
body{{margin:0;background:#f5f6f2;color:#142f2b;font:16px system-ui,sans-serif}}
main{{max-width:1000px;margin:auto;padding:48px 24px}}h1{{font-size:42px;letter-spacing:-1.5px}}
.tag{{font-size:12px;letter-spacing:2px;text-transform:uppercase}}p{{line-height:1.6}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px}}
.card{{background:white;border:1px solid #dce2db;border-radius:12px;padding:24px}}
.card strong{{display:block;font-size:30px;margin-top:12px}}section{{margin-top:40px}}
table{{width:100%;border-collapse:collapse;background:white}}th,td{{text-align:left;padding:16px;
border-bottom:1px solid #dce2db}}.bar{{display:flex;align-items:center;gap:20px;margin:24px 0}}
.bar span{{width:110px}}meter{{flex:1;height:28px}}a{{color:#146353}}
footer{{margin-top:48px;border-top:1px solid #cbd5ca;padding-top:20px;font-size:14px}}
</style><main><div class="tag">Python · DuckDB · dbt</div><h1>Retail performance</h1>
<p>Synthetic portfolio data · EUR · Generated from warehouse reporting tables</p>
<div class="cards"><div class="card">Net revenue<strong>{money(total)}</strong></div>
<div class="card">Completed orders<strong>{orders}</strong></div>
<div class="card">Order lines<strong>{lines}</strong></div>
<div class="card">Ingested batches<strong>{batches}</strong></div></div>
<section><h2>Revenue by category</h2>{bars}</section>
<section><h2>Daily sales</h2><table><thead><tr><th>Date</th><th>Net revenue</th>
<th>Completed orders</th></tr></thead><tbody>{rows}</tbody></table></section>
<footer>Revenue = completed line quantity × unit price − line discount. Cancelled lines contribute
zero. The example includes a late order, a price correction and a cancellation. Daily order counts
are distinct within each day; an order spanning dates must not be summed across days.<p>
<a href="https://github.com/JesU2504/retail-analytics-pipeline">Source and walkthrough</a>
</p>This is a local portfolio demonstration using synthetic data, with no customer records.</footer>
</main></html>"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return {"net_revenue_cents": total, "completed_orders": orders, "order_lines": lines}

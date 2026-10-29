# Interactive dashboard

Buildless HTML/CSS/JavaScript. The browser filters exported warehouse facts;
it does not execute Python, run dbt or connect to a cloud warehouse.

Features: date presets and custom ranges, category/country filters, daily revenue,
category and market breakdowns, order search/sorting/pagination, filtered CSV
export, ingestion batch audit and real dbt test results from the snapshot build.
Empty selections and invalid date ranges have explicit states. All order/revenue
metrics respect active filters. Quality checks apply to the full exported snapshot.

Run from the repository root with the Python environment active:

```bash
retail demo
retail showcase
python scripts/prepare_dashboard.py
python -m http.server 8000 --directory build/dashboard
```

Open `http://localhost:8000`. Serve through HTTP because the dashboard fetches
JSON snapshots. Opening index.html through a file URL will not work consistently.
Use Node.js 24 to run `node --test dashboard/model.test.mjs`.

`retail demo` preserves the four-line €320 validation example. `retail showcase`
creates a separate warehouse with 840 synthetic current lines across 90 days,
including corrections, cancellations and late-arriving records. Both commands
run dbt before exporting facts joined to product/customer dimensions. A failed
build stops the CLI; the exporter rejects missing or failed data tests.

To export an existing local warehouse after a fresh build:
`retail dashboard --database build/showcase.duckdb --output build/showcase.json`.
The demo datasets contain no real customer identities. Avoid packaging private
records into a public dashboard. The frontend and snapshots are served as static
assets; warehouse refreshes require rerunning the commands and republishing.

# Interview walkthrough

Start with the business question: how much completed revenue did the shop earn
per day and product category, after source corrections?

1. Run `retail demo`. Explain the €490 to €320 reconciliation using the discount
   correction, cancellation and late order. The report values come from SQL marts.
2. Open `src/retail_pipeline/ingest.py`. Show the transaction and explain why the
   dimensions, fact-source updates and batch audit must commit together. The
   rollback test deliberately changes a customer before encountering a bad FK.
3. Explain the difference between a content digest and a revision. The digest
   handles exact redelivery; revisions prevent stale data overwriting a correction.
4. Open `dbt/models/fact_order_lines.sql`. Its grain is one current line, not
   one order or one event. Explain why filtering by maximum order date would
   silently lose the late October 1 order after October 3 had already loaded.
5. Draw the three dimensions and fact. Explain SCD type 1, stable surrogate
   keys and why category marts rebuild when a product attribute changes.
6. Open the integration test. It compares incremental results with a full
   refresh and deliberately corrupts warehouse revenue to ensure dbt detects it.
7. State the limits: small synthetic data, one writer, separate load/build steps,
   no cloud warehouse credentials, no CDC delete feed or full version history.

Before using this project in an interview, run it yourself and change a fixture.
Try an invalid product reference, rerun a batch, and predict the revenue before
viewing the report. Be able to explain these choices in your own words.

References used for implementation:

- [DuckDB Python client](https://duckdb.org/docs/stable/clients/python/overview)
- [dbt incremental models](https://docs.getdbt.com/docs/build/incremental-models)
- [dbt DuckDB adapter](https://github.com/duckdb/dbt-duckdb)

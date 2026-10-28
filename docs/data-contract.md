# Source data contract

Each batch directory must contain three UTF-8 CSV files, even when one has only
its header. Column names and order must match exactly. Keys are case-sensitive
non-empty strings; duplicate keys within a file reject the whole batch.

| File | Columns in order |
| --- | --- |
| customers.csv | customer_id, country, segment |
| products.csv | product_id, product_name, category |
| order_lines.csv | line_id, order_id, customer_id, product_id, order_date, quantity, unit_price_cents, discount_cents, status, revision |

Customer/product batches are partial upserts, not snapshots with implied deletes.
Unmentioned records remain. Attributes use latest-arriving values. An exact
batch replay does not revert later attributes because its digest is already known.

Order lines represent current versions. `revision` must be a positive integer
that increases when any line field changes. An equal revision with different
content is an error; a lower revision is ignored. `order_date` must be ISO
YYYY-MM-DD. `quantity` is positive; `unit_price_cents` is non-negative;
`discount_cents` is the total line discount, between zero and gross line value.
`status` is `completed` or `cancelled`. Every referenced customer/product must
already exist or be included in the same batch.

All amounts are EUR integer cents. Tax, shipping and refunds are excluded.
An order can have multiple lines, but line IDs must be globally unique. Order
counts use distinct order IDs, so counts by date/category are not generally
additive. No global constraint enforces one date/customer per order ID.

The raw layer stores current line versions and a batch digest/audit, not every
historical payload. Keep original source files if full change-history retention
is required. The demo generator writes reproducible initial/update examples.

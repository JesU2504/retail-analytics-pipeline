{{ config(materialized='incremental', unique_key='line_id', incremental_strategy='delete+insert') }}
-- Grain: one current version per source order line. Batch order, not event date,
-- is the watermark so old-dated orders and corrections are not dropped.
select line_id, order_id, md5(customer_id) as customer_key,
    md5(product_id) as product_key, order_date as date_key,
    quantity, unit_price_cents, discount_cents, status, revision, batch_id,
    case when status = 'completed'
        then quantity * unit_price_cents - discount_cents else 0 end as net_revenue_cents
from {{ source('retail', 'order_lines') }}
{% if is_incremental() %}
where batch_id >= (select coalesce(max(batch_id), 0) from {{ this }})
{% endif %}

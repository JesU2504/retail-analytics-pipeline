select date_key as order_date, sum(net_revenue_cents) as net_revenue_cents,
    count(distinct case when status = 'completed' then order_id end) as completed_orders
from {{ ref('fact_order_lines') }}
group by date_key

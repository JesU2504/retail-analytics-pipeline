select p.category, sum(f.net_revenue_cents) as net_revenue_cents
from {{ ref('fact_order_lines') }} f
join {{ ref('dim_products') }} p using (product_key)
group by p.category

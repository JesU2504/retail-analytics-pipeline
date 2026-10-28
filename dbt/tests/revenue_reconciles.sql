-- Independently recompute revenue from raw records, including corrections/cancellations.
select 1 as mismatch
where (select coalesce(sum(net_revenue_cents), 0) from {{ ref('fact_order_lines') }})
    != (select coalesce(sum(case when status = 'completed'
            then quantity * unit_price_cents - discount_cents else 0 end), 0)
        from {{ source('retail', 'order_lines') }})
   or (select coalesce(sum(net_revenue_cents), 0) from {{ ref('mart_daily_sales') }})
    != (select coalesce(sum(net_revenue_cents), 0) from {{ ref('fact_order_lines') }})
   or (select coalesce(sum(net_revenue_cents), 0) from {{ ref('mart_category_sales') }})
    != (select coalesce(sum(net_revenue_cents), 0) from {{ ref('fact_order_lines') }})

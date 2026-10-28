select distinct order_date as date_key, year(order_date) as year_number,
    month(order_date) as month_number, day(order_date) as day_number
from {{ source('retail', 'order_lines') }}

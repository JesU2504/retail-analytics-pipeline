select md5(customer_id) as customer_key, customer_id, country, segment
from {{ source('retail', 'customers') }}

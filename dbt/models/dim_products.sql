select md5(product_id) as product_key, product_id, product_name, category
from {{ source('retail', 'products') }}

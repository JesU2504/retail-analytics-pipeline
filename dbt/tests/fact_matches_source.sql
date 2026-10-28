select 1 as mismatch
where (select count(*) from {{ ref('fact_order_lines') }})
    != (select count(*) from {{ source('retail', 'order_lines') }})
   or exists (
       select 1 from {{ ref('fact_order_lines') }} f
       join {{ source('retail', 'order_lines') }} r using (line_id)
       where f.revision != r.revision or f.batch_id != r.batch_id
   )

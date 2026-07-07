-- Cleansed Order Details: cast keys and numerics to proper types
with source as (

    select * from {{ source('raw', 'order_details') }}

)

select
    cast(orderid as integer)        as order_id,
    cast(productid as integer)      as product_id,
    cast(unitprice as number(10,2)) as unit_price,
    cast(quantity as integer)       as quantity,
    cast(discount as float)         as discount
from source

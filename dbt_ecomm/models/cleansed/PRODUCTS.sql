-- Cleansed Products: cast ids/numerics, trim text, discontinued as boolean
with source as (

    select * from {{ source('raw', 'products') }}

)

select
    cast(productid as integer)      as product_id,
    trim(productname)               as product_name,
    cast(supplierid as integer)     as supplier_id,
    cast(categoryid as integer)     as category_id,
    trim(quantityperunit)           as quantity_per_unit,
    cast(unitprice as number(10,2)) as unit_price,
    cast(unitsinstock as integer)   as units_in_stock,
    cast(unitsonorder as integer)   as units_on_order,
    cast(reorderlevel as integer)   as reorder_level,
    cast(discontinued as boolean)   as is_discontinued
from source

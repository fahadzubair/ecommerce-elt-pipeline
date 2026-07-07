-- DIM_PRODUCTS: product dimension built on the cleansed products model
with products as (

    select * from {{ ref('PRODUCTS') }}

)

select
    product_id,
    product_name,
    supplier_id,
    category_id,
    quantity_per_unit,
    unit_price,
    units_in_stock,
    units_on_order,
    reorder_level,
    is_discontinued
from products

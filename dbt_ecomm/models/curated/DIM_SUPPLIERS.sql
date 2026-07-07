-- DIM_SUPPLIERS: supplier dimension built on the cleansed suppliers model
with suppliers as (

    select * from {{ ref('SUPPLIERS') }}

)

select
    supplier_id,
    company_name,
    contact_name,
    contact_title,
    address,
    city,
    region,
    postal_code,
    country,
    phone,
    fax,
    home_page
from suppliers

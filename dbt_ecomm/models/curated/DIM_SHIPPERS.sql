-- DIM_SHIPPERS: shipper dimension built on the cleansed shippers model
with shippers as (

    select * from {{ ref('SHIPPERS') }}

)

select
    shipper_id,
    company_name,
    phone
from shippers

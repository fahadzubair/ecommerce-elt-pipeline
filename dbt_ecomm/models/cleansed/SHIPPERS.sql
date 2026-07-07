-- Cleansed Shippers: cast id + trim text
with source as (

    select * from {{ source('raw', 'shippers') }}

)

select
    cast(shipperid as integer) as shipper_id,
    trim(companyname)          as company_name,
    trim(phone)                as phone
from source

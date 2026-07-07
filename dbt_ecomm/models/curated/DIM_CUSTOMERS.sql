-- DIM_CUSTOMERS: customer dimension built on the cleansed customers model
with customers as (

    select * from {{ ref('CUSTOMERS') }}

)

select
    customer_id,
    company_name,
    contact_name,
    contact_title,
    address,
    city,
    region,
    postal_code,
    country,
    phone,
    fax
from customers

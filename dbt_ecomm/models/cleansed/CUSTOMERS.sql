-- Cleansed Customers: rename to snake_case + trim text fields
with source as (

    select * from {{ source('raw', 'customers') }}

)

select
    trim(customerid)   as customer_id,   -- alphanumeric code, keep as text
    trim(companyname)  as company_name,
    trim(contactname)  as contact_name,
    trim(contacttitle) as contact_title,
    trim(address)      as address,
    trim(city)         as city,
    trim(region)       as region,
    trim(postalcode)   as postal_code,
    trim(country)      as country,
    trim(phone)        as phone,
    trim(fax)          as fax
from source

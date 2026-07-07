-- Cleansed Suppliers: cast id + trim text fields
with source as (

    select * from {{ source('raw', 'suppliers') }}

)

select
    cast(supplierid as integer) as supplier_id,
    trim(companyname)           as company_name,
    trim(contactname)           as contact_name,
    trim(contacttitle)          as contact_title,
    trim(address)               as address,
    trim(city)                  as city,
    trim(region)                as region,
    trim(postalcode)            as postal_code,
    trim(country)               as country,
    trim(phone)                 as phone,
    trim(fax)                   as fax,
    trim(homepage)              as home_page
from source

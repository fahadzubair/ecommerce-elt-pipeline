-- Cleansed Orders: cast ids/dates, trim shipping text fields
with source as (

    select * from {{ source('raw', 'orders') }}

)

select
    cast(orderid as integer)     as order_id,
    trim(customerid)             as customer_id,   -- alphanumeric code
    cast(employeeid as integer)  as employee_id,
    cast(orderdate as date)      as order_date,
    cast(requireddate as date)   as required_date,
    cast(shippeddate as date)    as shipped_date,
    cast(shipvia as integer)     as ship_via,
    cast(freight as number(10,2)) as freight,
    trim(shipname)               as ship_name,
    trim(shipaddress)            as ship_address,
    trim(shipcity)               as ship_city,
    trim(shipregion)             as ship_region,
    trim(shippostalcode)         as ship_postal_code,
    trim(shipcountry)            as ship_country
from source

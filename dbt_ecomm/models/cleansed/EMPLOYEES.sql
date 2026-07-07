-- Cleansed Employees: type-cast ids/dates, trim text, drop the photo blob
with source as (

    select * from {{ source('raw', 'employees') }}

)

select
    cast(employeeid as integer) as employee_id,
    trim(lastname)              as last_name,
    trim(firstname)             as first_name,
    trim(title)                 as title,
    trim(titleofcourtesy)       as title_of_courtesy,
    cast(birthdate as date)     as birth_date,
    cast(hiredate as date)      as hire_date,
    trim(address)               as address,
    trim(city)                  as city,
    trim(region)                as region,
    trim(postalcode)            as postal_code,
    trim(country)               as country,
    trim(homephone)             as home_phone,
    trim(extension)             as extension,
    trim(notes)                 as notes,
    cast(reportsto as integer)  as reports_to
    -- "photo" column dropped: base64 image blob, not useful downstream
from source

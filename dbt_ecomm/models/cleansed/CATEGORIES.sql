-- Cleansed Categories: raw -> cleansed with minimal, basic transformations
with source as (
    select * from {{ source('raw', 'categories') }}
)

select
    cast(categoryid as integer) as category_id,   -- enforce a proper type
    trim(categoryname)          as category_name,  -- rename + strip whitespace
    description
from source

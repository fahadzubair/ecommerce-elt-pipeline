-- Cleansed Territories: keep id as text, trim (values have trailing spaces)
with source as (

    select * from {{ source('raw', 'territories') }}

)

select
    trim(territoryid)          as territory_id,   -- numeric-looking code, keep as text
    trim(territorydescription) as territory_description,
    cast(regionid as integer)  as region_id
from source

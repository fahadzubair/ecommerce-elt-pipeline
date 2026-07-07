-- Cleansed Regions: cast id + trim (source values have trailing spaces)
with source as (

    select * from {{ source('raw', 'regions') }}

)

select
    cast(regionid as integer)  as region_id,
    trim(regiondescription)    as region_description
from source

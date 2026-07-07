-- DIM_REGIONS: region dimension built on the cleansed regions model
with regions as (

    select * from {{ ref('REGIONS') }}

)

select
    region_id,
    region_description
from regions

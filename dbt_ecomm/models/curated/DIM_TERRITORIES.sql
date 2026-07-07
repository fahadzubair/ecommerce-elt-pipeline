-- DIM_TERRITORIES: territory dimension built on the cleansed territories model
with territories as (

    select * from {{ ref('TERRITORIES') }}

)

select
    territory_id,
    territory_description,
    region_id
from territories

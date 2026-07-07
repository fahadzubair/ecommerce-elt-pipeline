-- DIM_CATEGORIES: category dimension built on the cleansed categories model
with categories as (

    select * from {{ ref('CATEGORIES') }}

)

select
    category_id,
    category_name,
    description
from categories

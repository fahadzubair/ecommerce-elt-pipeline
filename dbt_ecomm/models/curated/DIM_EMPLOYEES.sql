-- DIM_EMPLOYEES: employee dimension built on the cleansed employees model
with employees as (

    select * from {{ ref('EMPLOYEES') }}

)

select
    employee_id,
    first_name,
    last_name,
    title,
    title_of_courtesy,
    birth_date,
    hire_date,
    address,
    city,
    region,
    postal_code,
    country,
    home_phone,
    extension,
    reports_to
from employees

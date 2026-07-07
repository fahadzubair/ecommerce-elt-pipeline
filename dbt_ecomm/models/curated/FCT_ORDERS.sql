-- FCT_ORDERS: sales fact at the order-line grain (one row per order + product).
-- Joins order details to their parent order for the dimension keys and dates.
with order_details as (

    select * from {{ ref('ORDER_DETAILS') }}

),

orders as (

    select * from {{ ref('ORDERS') }}

)

select
    -- dimension keys
    od.order_id,
    od.product_id,
    o.customer_id,
    o.employee_id,
    o.ship_via as shipper_id,

    -- order dates
    o.order_date,
    o.required_date,
    o.shipped_date,

    -- measures
    od.unit_price,
    od.quantity,
    od.discount,
    (od.unit_price * od.quantity * (1 - od.discount)) as net_amount

from order_details od
left join orders o
    on od.order_id = o.order_id

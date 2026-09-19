select
    customer_id,
    trim(customer_name)  as customer_name,
    lower(trim(email))   as email,
    plan,
    cast(signup_date as date) as signup_date
from raw.customers

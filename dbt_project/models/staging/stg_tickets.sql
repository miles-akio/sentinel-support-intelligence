select
    ticket_id,
    customer_id,
    cast(created_at as timestamp) as created_at,
    subject,
    body
from raw.tickets

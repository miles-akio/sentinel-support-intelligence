-- Grain: one row per ticket, enriched with AI-derived fields.
-- This is the core fact table everything downstream rolls up from.

with tickets as (
    select * from {{ ref('stg_tickets') }}
),

enrichment as (
    select * from {{ ref('stg_ticket_enrichment') }}
),

customers as (
    select * from {{ ref('stg_customers') }}
)

select
    t.ticket_id,
    t.created_at,
    date_trunc('day', t.created_at) as created_date,
    t.customer_id,
    c.plan,
    t.subject,
    t.body,
    e.category,
    e.urgency,
    e.sentiment_score,
    e.summary
from tickets t
left join enrichment e on t.ticket_id = e.ticket_id
left join customers c  on t.customer_id = c.customer_id

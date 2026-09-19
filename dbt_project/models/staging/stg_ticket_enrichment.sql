-- This staging model is the boundary between "raw LLM output" and
-- "trusted structured field" from the rest of the warehouse's perspective.
-- By the time downstream models reference this, it's just another column.

select
    ticket_id,
    category,
    urgency,
    sentiment_score,
    summary
from raw.ticket_enrichment

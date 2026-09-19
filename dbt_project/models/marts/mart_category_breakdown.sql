select
    category,
    count(*)                       as num_tickets,
    round(avg(sentiment_score), 3) as avg_sentiment,
    sum(case when urgency = 'high' then 1 else 0 end)   as high_urgency_count,
    round(100.0 * sum(case when urgency = 'high' then 1 else 0 end) / count(*), 1) as pct_high_urgency
from {{ ref('fct_tickets') }}
group by 1
order by num_tickets desc

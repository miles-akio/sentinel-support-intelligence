select
    created_date,
    count(*)                          as num_tickets,
    round(avg(sentiment_score), 3)    as avg_sentiment,
    sum(case when urgency = 'high' then 1 else 0 end) as high_urgency_tickets
from {{ ref('fct_tickets') }}
group by 1
order by 1

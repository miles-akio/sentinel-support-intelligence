-- Business-relevant cut: is a particular pricing plan generating a
-- disproportionate amount of negative-sentiment or urgent tickets?
-- (a classic use of AI-derived fields feeding a business decision)

select
    plan,
    count(*)                       as num_tickets,
    round(avg(sentiment_score), 3) as avg_sentiment,
    sum(case when urgency = 'high' then 1 else 0 end) as high_urgency_count
from {{ ref('fct_tickets') }}
group by 1
order by avg_sentiment asc

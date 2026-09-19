"""
schemas.py
----------
Two contracts:
  1. What a raw ticket must look like (basic sanity on the source data).
  2. What the LLM's output must look like — this is the more important one.

LLMs occasionally produce malformed or unexpected values (a category not in
the allowed list, a sentiment score out of range, a missing field). Treating
LLM output as untrusted, structured data — subject to the same validation
gate as anything from an external API — is the difference between a hobby
project and a production-grade AI pipeline.
"""

import pandera as pa
from pandera import Column, Check

CATEGORIES = ["billing", "bug", "account_access", "feature_request", "shipping", "other"]

tickets_schema = pa.DataFrameSchema(
    {
        "ticket_id": Column(int, unique=True, nullable=False),
        "customer_id": Column(int, nullable=False),
        "created_at": Column(str, nullable=False),
        "subject": Column(str, nullable=False),
        "body": Column(str, nullable=False),
    },
    strict=False,
)

customers_schema = pa.DataFrameSchema(
    {
        "customer_id": Column(int, unique=True, nullable=False),
        "customer_name": Column(str, nullable=False),
        "email": Column(str, nullable=False),
        "plan": Column(str, nullable=False),
        "signup_date": Column(str, nullable=False),
    }
)

# The important one: validates Claude's (or the mock fallback's) output
# before it's trusted anywhere downstream.
enrichment_schema = pa.DataFrameSchema(
    {
        "ticket_id": Column(int, unique=True, nullable=False),
        "category": Column(str, Check.isin(CATEGORIES), nullable=False),
        "urgency": Column(str, Check.isin(["low", "medium", "high"]), nullable=False),
        "sentiment_score": Column(float, Check.in_range(-1.0, 1.0), nullable=False, coerce=True),
        "summary": Column(str, nullable=False),
    }
)

"""
test_schemas.py
----------------
Verifies the Pandera contracts actually catch bad data — both the raw
data contracts and, most importantly, the LLM-output contract. A schema
that never rejects anything isn't actually validating anything.
"""

import pandas as pd
import pytest
from pandera.errors import SchemaError

from schemas import tickets_schema, customers_schema, enrichment_schema


# ---------------------------------------------------------------------
# tickets_schema
# ---------------------------------------------------------------------

def test_valid_tickets_pass():
    df = pd.DataFrame(
        {
            "ticket_id": [1, 2],
            "customer_id": [10, 11],
            "created_at": ["2026-06-01 10:00:00", "2026-06-02 11:00:00"],
            "subject": ["Can't log in", "Billing question"],
            "body": ["I can't log into my account.", "I was charged twice."],
        }
    )
    # Should not raise
    tickets_schema.validate(df)


def test_duplicate_ticket_id_fails():
    df = pd.DataFrame(
        {
            "ticket_id": [1, 1],  # duplicate -> violates uniqueness
            "customer_id": [10, 11],
            "created_at": ["2026-06-01 10:00:00", "2026-06-02 11:00:00"],
            "subject": ["a", "b"],
            "body": ["a", "b"],
        }
    )
    with pytest.raises(SchemaError):
        tickets_schema.validate(df)


def test_null_body_fails():
    df = pd.DataFrame(
        {
            "ticket_id": [1],
            "customer_id": [10],
            "created_at": ["2026-06-01 10:00:00"],
            "subject": ["a"],
            "body": [None],
        }
    )
    with pytest.raises(SchemaError):
        tickets_schema.validate(df)


# ---------------------------------------------------------------------
# customers_schema
# ---------------------------------------------------------------------

def test_valid_customers_pass():
    df = pd.DataFrame(
        {
            "customer_id": [1, 2],
            "customer_name": ["Alice", "Bob"],
            "email": ["a@example.com", "b@example.com"],
            "plan": ["Pro", "Team"],
            "signup_date": ["2025-01-01", "2025-02-01"],
        }
    )
    customers_schema.validate(df)


# ---------------------------------------------------------------------
# enrichment_schema — THE important one: this is the contract the LLM's
# (or the mock fallback's) output must satisfy before it's trusted.
# ---------------------------------------------------------------------

def test_valid_enrichment_passes():
    df = pd.DataFrame(
        {
            "ticket_id": [1, 2],
            "category": ["billing", "bug"],
            "urgency": ["high", "low"],
            "sentiment_score": [-0.5, 0.2],
            "summary": ["Overcharged customer", "App crash report"],
        }
    )
    enrichment_schema.validate(df)


def test_invalid_category_rejected():
    """An LLM hallucinating a category outside the allowed list must fail validation."""
    df = pd.DataFrame(
        {
            "ticket_id": [1],
            "category": ["not_a_real_category"],
            "urgency": ["high"],
            "sentiment_score": [-0.5],
            "summary": ["test"],
        }
    )
    with pytest.raises(SchemaError):
        enrichment_schema.validate(df)


def test_invalid_urgency_rejected():
    df = pd.DataFrame(
        {
            "ticket_id": [1],
            "category": ["billing"],
            "urgency": ["super_urgent"],  # not in ["low", "medium", "high"]
            "sentiment_score": [-0.5],
            "summary": ["test"],
        }
    )
    with pytest.raises(SchemaError):
        enrichment_schema.validate(df)


def test_out_of_range_sentiment_rejected():
    """Sentiment must be between -1.0 and 1.0 — a model returning 5.0 must be caught."""
    df = pd.DataFrame(
        {
            "ticket_id": [1],
            "category": ["billing"],
            "urgency": ["high"],
            "sentiment_score": [5.0],
            "summary": ["test"],
        }
    )
    with pytest.raises(SchemaError):
        enrichment_schema.validate(df)


def test_duplicate_enrichment_ticket_id_rejected():
    df = pd.DataFrame(
        {
            "ticket_id": [1, 1],
            "category": ["billing", "bug"],
            "urgency": ["high", "low"],
            "sentiment_score": [-0.5, 0.1],
            "summary": ["a", "b"],
        }
    )
    with pytest.raises(SchemaError):
        enrichment_schema.validate(df)

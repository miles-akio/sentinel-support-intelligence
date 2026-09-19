"""
test_llm_enrich.py
--------------------
Tests the mock-mode enrichment logic (the offline fallback) for correctness,
and end-to-end tests that `enrich_tickets()` always produces output
conforming to the enrichment schema regardless of which ticket text it's
given. Live Claude calls are NOT tested here (no API key in CI/this
environment) — see test_llm_enrich_live.py for how to test the real path
if you have a key.
"""

import os

import polars as pl
import pytest

from llm_enrich import _mock_enrich, enrich_tickets
from schemas import enrichment_schema


# ---------------------------------------------------------------------
# _mock_enrich: exact expected-output tests for known input patterns
# ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "text,expected_category",
    [
        ("I was charged twice for my Pro subscription this month.", "billing"),
        ("The app crashes every time I open the dashboard.", "bug"),
        ("I can't log in, it says my password is incorrect.", "account_access"),
        ("Could you add dark mode support? Would be really helpful.", "feature_request"),
        ("My order still hasn't arrived, tracking shows no updates.", "shipping"),
        ("Just wanted to say the product is great, thanks!", "other"),
    ],
)
def test_mock_enrich_category_detection(text, expected_category):
    result = _mock_enrich(text)
    assert result["category"] == expected_category


def test_mock_enrich_flags_urgent_language():
    urgent_text = "This is extremely urgent, I need this resolved immediately."
    calm_text = "Whenever you get a chance, could you look into this?"

    assert _mock_enrich(urgent_text)["urgency"] == "high"
    assert _mock_enrich(calm_text)["urgency"] != "high"


def test_mock_enrich_negative_sentiment_for_harsh_language():
    negative_text = "The app crashes constantly, this is broken and unacceptable."
    neutral_text = "Could you add CSV export to the reports page?"

    neg_result = _mock_enrich(negative_text)
    neutral_result = _mock_enrich(neutral_text)

    assert neg_result["sentiment_score"] < neutral_result["sentiment_score"]


def test_mock_enrich_output_shape():
    result = _mock_enrich("Some ticket text.")
    assert set(result.keys()) == {"category", "urgency", "sentiment_score", "summary"}
    assert isinstance(result["sentiment_score"], float)
    assert -1.0 <= result["sentiment_score"] <= 1.0


# ---------------------------------------------------------------------
# enrich_tickets: end-to-end, output must always satisfy the schema
# ---------------------------------------------------------------------

def test_enrich_tickets_produces_schema_valid_output(monkeypatch):
    # Force mock mode regardless of the environment running these tests.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    tickets = pl.DataFrame(
        {
            "ticket_id": [1, 2, 3],
            "customer_id": [10, 11, 12],
            "created_at": ["2026-06-01", "2026-06-02", "2026-06-03"],
            "subject": ["a", "b", "c"],
            "body": [
                "I was charged twice for my subscription, please refund me immediately.",
                "The dashboard keeps crashing on my phone.",
                "Could you add bulk editing to the reports tab?",
            ],
        }
    )

    enriched = enrich_tickets(tickets)

    assert enriched.shape[0] == 3
    assert set(enriched.columns) == {"ticket_id", "category", "urgency", "sentiment_score", "summary"}

    # This is the real assertion that matters: the output must pass the
    # same Pandera contract the pipeline enforces before loading to the warehouse.
    enrichment_schema.validate(enriched.to_pandas())


def test_enrich_tickets_ticket_ids_preserved_and_unique():
    tickets = pl.DataFrame(
        {
            "ticket_id": [101, 102],
            "customer_id": [1, 2],
            "created_at": ["2026-06-01", "2026-06-02"],
            "subject": ["a", "b"],
            "body": ["Billing issue with my invoice.", "App crashes on load."],
        }
    )
    enriched = enrich_tickets(tickets)
    assert sorted(enriched["ticket_id"].to_list()) == [101, 102]


def test_enrich_tickets_accepts_csv_path_and_writes_parquet(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    csv_path = tmp_path / "tickets.csv"
    csv_path.write_text(
        "ticket_id,customer_id,created_at,subject,body\n"
        "1,10,2026-06-01,Billing issue,The customer was charged twice for the Pro plan.\n"
        "2,11,2026-06-02,Login issue,My app crashes every time I click sign in.\n"
    )

    out_dir = tmp_path / "output"
    enriched = enrich_tickets(csv_path, out_dir)

    assert enriched.shape[0] == 2
    assert (out_dir / "ticket_enrichment.parquet").exists()
    assert set(enriched.columns) == {"ticket_id", "category", "urgency", "sentiment_score", "summary"}

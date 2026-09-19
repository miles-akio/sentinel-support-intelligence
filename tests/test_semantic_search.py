"""
test_semantic_search.py
-------------------------
Verifies the retrieval layer actually returns relevant results — the
"correct output" check for the RAG pattern's retrieval half.
"""

import polars as pl

from semantic_search import build_index, search


SAMPLE_TICKETS = pl.DataFrame(
    {
        "ticket_id": [1, 2, 3, 4, 5],
        "subject": ["a", "b", "c", "d", "e"],
        "body": [
            "The app crashes every time I open the dashboard on my phone.",
            "I was charged twice for my Pro subscription this month, please refund me.",
            "My package arrived damaged, the box was completely crushed.",
            "The dashboard freezes and shows a blank screen after the update.",
            "Could you add dark mode support to the settings page?",
        ],
    }
)


def test_search_returns_requested_number_of_results():
    vectorizer, matrix = build_index(SAMPLE_TICKETS)
    results = search("app is broken", SAMPLE_TICKETS, vectorizer, matrix, top_k=3)
    assert results.shape[0] == 3


def test_search_ranks_relevant_ticket_first():
    """A billing-specific query should rank the billing ticket above unrelated ones."""
    vectorizer, matrix = build_index(SAMPLE_TICKETS)
    results = search("overcharged subscription refund", SAMPLE_TICKETS, vectorizer, matrix, top_k=1)
    assert results["ticket_id"][0] == 2


def test_search_ranks_crash_tickets_above_unrelated_tickets():
    vectorizer, matrix = build_index(SAMPLE_TICKETS)
    results = search("dashboard crashing and freezing", SAMPLE_TICKETS, vectorizer, matrix, top_k=2)
    top_two_ids = set(results["ticket_id"].to_list())
    # tickets 1 and 4 are the crash/freeze-related ones
    assert top_two_ids == {1, 4}


def test_similarity_scores_are_sorted_descending():
    vectorizer, matrix = build_index(SAMPLE_TICKETS)
    results = search("damaged package delivery", SAMPLE_TICKETS, vectorizer, matrix, top_k=5)
    scores = results["similarity"].to_list()
    assert scores == sorted(scores, reverse=True)

"""
semantic_search.py
--------------------
Provides "find tickets similar to this query" — the retrieval half of a
RAG (retrieval-augmented generation) pattern, used later by the dashboard's
"Ask AI" feature.

A NOTE ON EMBEDDINGS: in a real 2026 production setup, you'd typically pair
Claude (for generation/reasoning) with a dedicated embeddings model —
Voyage AI (Anthropic's recommended embeddings partner) or OpenAI embeddings
— to get true semantic vector search. This sandbox's network is restricted
to package registries only (no calls to embedding APIs), so this module
uses TF-IDF + cosine similarity as a fully offline, dependency-light stand-in
that demonstrates the exact same retrieval pattern. Swapping in real
embeddings later is a ~10-line change — see `get_embedder()` below.
"""

from pathlib import Path

import numpy as np
import polars as pl
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = Path(__file__).resolve().parent.parent


def get_embedder():
    """
    Swap point: replace this with a real embeddings call, e.g.

        import voyageai
        vo = voyageai.Client()  # reads VOYAGE_API_KEY from env
        def embed(texts):
            return np.array(vo.embed(texts, model="voyage-3").embeddings)
        return embed

    and swap TfidfVectorizer usage below for `embed(...)` calls.
    """
    vectorizer = TfidfVectorizer(stop_words="english", max_features=2000)
    return vectorizer


def build_index(tickets: pl.DataFrame):
    """Fits a TF-IDF index over ticket bodies. Returns (vectorizer, matrix)."""
    vectorizer = get_embedder()
    matrix = vectorizer.fit_transform(tickets["body"].to_list())
    return vectorizer, matrix


def search(query: str, tickets: pl.DataFrame, vectorizer, matrix, top_k: int = 5) -> pl.DataFrame:
    """Returns the top_k tickets most similar to the query."""
    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, matrix).flatten()
    top_idx = np.argsort(scores)[::-1][:top_k]

    results = tickets[top_idx.tolist()].with_columns(
        pl.Series("similarity", scores[top_idx].round(3))
    )
    return results


if __name__ == "__main__":
    # Quick smoke test
    tickets = pl.read_parquet(BASE_DIR / "data" / "processed" / "tickets.parquet")
    vectorizer, matrix = build_index(tickets)
    result = search("app keeps crashing on my phone", tickets, vectorizer, matrix, top_k=3)
    print(result.select(["ticket_id", "subject", "similarity"]))

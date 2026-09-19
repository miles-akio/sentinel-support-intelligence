"""
app.py
------
The analyst-facing dashboard. Three things happening here:

1. Standard BI: KPIs, trends, and breakdowns read straight from dbt marts
   (same pattern as any conventional analytics dashboard).
2. Semantic search: free-text query -> TF-IDF retrieval over ticket bodies
   (see enrichment/semantic_search.py).
3. "Ask AI": a small RAG loop — retrieve the most relevant tickets for the
   user's question, then hand them to Claude as context so it answers
   grounded in your actual ticket data instead of guessing. Falls back to
   a canned message if no ANTHROPIC_API_KEY is set.

Run:
    streamlit run dashboard/app.py
"""

import os
import sys
from pathlib import Path

import duckdb
import plotly.express as px
import polars as pl
import streamlit as st
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")  # picks up ANTHROPIC_API_KEY from a .env file if present
sys.path.insert(0, str(BASE_DIR / "enrichment"))
from semantic_search import build_index, search  # noqa: E402

DB_PATH = BASE_DIR / "warehouse.duckdb"

st.set_page_config(page_title="AI Support Ticket Intelligence", layout="wide")


@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_resource
def get_search_index():
    tickets = pl.read_parquet(BASE_DIR / "data" / "processed" / "tickets.parquet")
    vectorizer, matrix = build_index(tickets)
    return tickets, vectorizer, matrix


con = get_connection()
tickets_df, vectorizer, matrix = get_search_index()

st.title("🤖 AI-Powered Support Ticket Intelligence")
st.caption("Claude classifies, scores, and summarizes every ticket; dbt models the results; this dashboard surfaces the insights.")

daily = con.execute("SELECT * FROM mart_daily_ticket_trends ORDER BY created_date").df()
category = con.execute("SELECT * FROM mart_category_breakdown").df()
plan_health = con.execute("SELECT * FROM mart_plan_health").df()

# ---- KPI row ----
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Tickets", f"{daily['num_tickets'].sum():,}")
col2.metric("Avg Sentiment", f"{daily['num_tickets'].dot(daily['avg_sentiment']) / daily['num_tickets'].sum():.2f}")
col3.metric("High-Urgency Tickets", f"{daily['high_urgency_tickets'].sum():,}")
col4.metric(
    "% High Urgency",
    f"{100 * daily['high_urgency_tickets'].sum() / daily['num_tickets'].sum():.1f}%",
)

st.divider()

# ---- Trends ----
st.subheader("Ticket Volume & Sentiment Over Time")
fig_trend = px.line(daily, x="created_date", y=["num_tickets", "high_urgency_tickets"], markers=False)
fig_trend.update_layout(margin=dict(l=0, r=0, t=10, b=0))
st.plotly_chart(fig_trend, use_container_width=True)

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Tickets by AI-Classified Category")
    fig_cat = px.bar(category.sort_values("num_tickets"), x="num_tickets", y="category", orientation="h", color="avg_sentiment", color_continuous_scale="RdYlGn")
    fig_cat.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_cat, use_container_width=True)

with col_b:
    st.subheader("Ticket Health by Pricing Plan")
    st.dataframe(plan_health, use_container_width=True, hide_index=True)
    st.caption("Sorted by sentiment — plans with the most negative AI-scored sentiment surface first.")

st.divider()

# ---- Semantic search ----
st.subheader("🔎 Semantic Ticket Search")
st.caption("Retrieval layer of the RAG pattern below — finds tickets by meaning, not just keyword match.")
query = st.text_input("Search tickets", placeholder="e.g. customers complaining about being overcharged")
if query:
    results = search(query, tickets_df, vectorizer, matrix, top_k=5)
    st.dataframe(results.select(["ticket_id", "subject", "similarity"]).to_pandas(), use_container_width=True, hide_index=True)

st.divider()

# ---- Ask AI (RAG) ----
st.subheader("💬 Ask AI About Your Tickets")
mode = "LIVE (Claude API)" if os.environ.get("ANTHROPIC_API_KEY") else "OFFLINE (no ANTHROPIC_API_KEY set)"
st.caption(f"Mode: {mode}. Retrieves the most relevant tickets, then asks Claude to answer grounded in them.")

question = st.text_input("Ask a question", placeholder="What's the most common complaint about billing this month?")
if st.button("Ask") and question:
    relevant = search(question, tickets_df, vectorizer, matrix, top_k=8)
    context = "\n\n".join(
        f"Ticket #{row['ticket_id']}: {row['body']}" for row in relevant.iter_rows(named=True)
    )

    if os.environ.get("ANTHROPIC_API_KEY"):
        from anthropic import Anthropic
        client = Anthropic()
        with st.spinner("Asking Claude..."):
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=400,
                system="Answer the user's question using ONLY the ticket context provided. Be concise and specific, citing ticket numbers where relevant.",
                messages=[{"role": "user", "content": f"Context tickets:\n{context}\n\nQuestion: {question}"}],
            )
            st.write(response.content[0].text)
    else:
        st.info(
            "No ANTHROPIC_API_KEY set, so this is showing the retrieved context Claude would "
            "reason over rather than a generated answer. Set the key and re-run to get a live response."
        )
        st.text(context[:1500] + ("..." if len(context) > 1500 else ""))

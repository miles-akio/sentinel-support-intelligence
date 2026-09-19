# Project Overview

## Why this project exists

This project demonstrates a realistic support-analytics pipeline that blends modern data engineering, schema validation, and LLM-assisted enrichment into one end-to-end workflow. The goal is to show how raw customer support data can be transformed from unstructured text into a structured, queryable, and business-friendly dataset that can drive analytics, monitoring, and AI-powered question answering.

The project tackles the common challenge of turning noisy support tickets into trustworthy operational insight:

- support tickets arrive as messy free-form text
- the text needs to be categorized and scored consistently
- bad or malformed outputs must be rejected before they reach the warehouse
- analyst dashboards need clean, trusted data
- teams want to ask natural-language questions over real ticket history without hallucination

---

## What the project solves

The application models a complete support intelligence workflow:

1. Generate realistic customer and support ticket data.
2. Enrich each ticket with AI-produced metadata like category, urgency, sentiment, and summary.
3. Validate both the raw and enriched data using schema contracts.
4. Load trusted data into a local warehouse.
5. Transform it into curated analysis models with dbt.
6. Expose metrics, trends, and search in a dashboard.
7. Support an LLM-grounded Q&A layer over the ticket corpus.

This is useful for teams that want the same engineering discipline used in production data pipelines while also adding an LLM layer that is grounded in real records.

---

## Core architecture

The system is arranged around a standard analytics stack with AI components added in carefully controlled places:

- Generation: simulated support data is produced in the ingestion layer.
- Enrichment: LLM classification and summarization add structured fields to each ticket.
- Validation: Pandera checks ensure the outputs are within the expected contract.
- Storage: DuckDB stores the raw warehouse tables.
- Modeling: dbt creates staging and mart tables for business reporting.
- Visualization: Streamlit displays KPIs and trends.
- Retrieval: semantic search surfaces the most relevant tickets for a query.
- Answer generation: LLM answers are grounded in retrieved tickets instead of free-form guesses.

---

## Integrated processes

### 1. Data generation

The ingestion step creates synthetic support data for customers and tickets. The generated records include realistic complaint patterns across business categories such as billing, bugs, account access, feature requests, and shipping.

This simulates a production-like customer operations dataset without depending on a live commercial source.

### 2. LLM enrichment

Each ticket text is processed to derive:

- category
- urgency
- sentiment_score
- summary

The project supports two modes:

- mock mode: uses offline heuristics when no API key is configured
- live mode: uses Anthropic Claude when `ANTHROPIC_API_KEY` is present

The enrichment layer treats AI output as untrusted input until it passes validation.

### 3. Validation gate

Before data is allowed into the warehouse, schema validation is performed. This is critical because LLM output can be inconsistent or malformed.

The validation step checks:

- raw customer fields
- ticket fields
- enrichment fields
- allowed categories and urgency levels
- numeric ranges and required columns

By validating at this stage, the pipeline prevents bad records from polluting downstream models.

### 4. DuckDB warehouse loading

Validated raw datasets are loaded into a local DuckDB database. This creates the base warehouse needed for analytics and retrieval.

### 5. dbt data modeling

The dbt project handles data staging and mart creation:

- staging models clean and normalize the raw tables
- mart models produce business-ready fact and summary tables
- tests assert non-null, unique, and accepted-value constraints

This turns raw operational data into a trusted analytics layer with repeatable transformations.

### 6. Dashboard and BI layer

The Streamlit app reads from the dbt marts and displays:

- total ticket volume
- average sentiment
- high-urgency ticket counts
- trends over time
- category distribution
- plan-level sentiment health

This gives the business a practical view of the support operation without needing to analyze raw data directly.

### 7. Semantic search and RAG

The project has a retrieval layer that uses TF-IDF and cosine similarity to search tickets by meaning instead of strict keyword matching.

Then it adds a small retrieval-augmented generation flow:

- retrieve the most relevant tickets for a user question
- pass those tickets as evidence to Claude
- answer from the retrieved context instead of hallucinating

This is a strong pattern for grounded LLM application design.

---

## Mock mode vs live mode

The project is designed to run without external API access by default. This is important for local development, tests, and CI-like environments.

### Mock mode

Used when no API key is set.

- enrichment uses keyword heuristics
- no external network call is required
- the pipeline still runs fully offline

### Live mode

Used when `ANTHROPIC_API_KEY` is configured.

- real Claude calls process each ticket
- category, urgency, sentiment, and summary come from the model
- the dashboard can answer user questions grounded in retrieved ticket context

This pattern mirrors a realistic production setup where AI is treated as a downstream dependency with a fallback path.

---

## Why this design matters

This project is not just a toy example. It demonstrates a practical architecture for operational AI in data systems:

- AI-generated data is structured and validated before it becomes trusted
- analytics logic is separated cleanly from orchestration logic
- data quality checks are explicit, not implicit
- LLM usage is grounded in retrieved evidence, not detached reasoning
- the pipeline can be run fully offline for development and CI

In other words, it shows how to use AI in a way that is both useful and operationally defensible.

---

## Typical execution flow

The project flow is:

1. generate raw ticket data
2. enrich with classification metadata
3. validate all incoming and generated data
4. load into DuckDB
5. run dbt models and tests
6. inspect dashboard outputs
7. ask natural-language questions over the ticket corpus

The orchestration layer handles this as a single pipeline so multiple steps can run consistently and repeatably.

---

## Summary

This project is a full-stack support analytics prototype that demonstrates how a team can combine:

- synthetic data generation
- data validation
- AI enrichment
- warehouse loading
- transformation modeling
- business reporting
- semantic retrieval
- grounded question answering

The result is a realistic example of AI-powered support intelligence that is structured, auditable, and operationally practical.

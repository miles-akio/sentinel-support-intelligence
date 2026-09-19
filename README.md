# AI-Powered Support Ticket Intelligence — LLM + Data Analytics Project (2026)

A complete, runnable project that combines a production-style data pipeline
with an LLM layer: Claude classifies, scores, and summarizes raw customer
support tickets, and the rest of the stack (validation, warehouse, dbt,
orchestration, dashboard) treats that AI output the same way it would treat
any other trusted data source — after validating it first.

**Every step below has been run and verified working**, including a fully
offline "mock mode" so you can run the entire thing without an API key, and
a real Claude-powered mode you can switch on with one environment variable.

---

## 1. Architecture overview

```
Raw tickets (CSV, simulated support-desk export)  [ingestion/generate_raw_tickets.py]
      |
      v
LLM enrichment: Claude classifies category, urgency,        [enrichment/llm_enrich.py]
sentiment, and summary for each ticket
(falls back to an offline heuristic if no API key is set)
      |
      v
Validate raw data AND LLM output (Pandera)                  [validation/validate_all.py]
      |
      v
Load into DuckDB "raw" schema                                [ingestion/load_to_duckdb.py]
      |
      v
dbt: staging models (1:1 cleanup)                             [dbt_project/models/staging/]
      |
      v
dbt: mart models (join tickets + customers + AI fields)        [dbt_project/models/marts/]
      |
      v
dbt tests (including checks that Claude's own category/urgency
output falls within the allowed contract)
      |
      v
Streamlit dashboard: KPIs + trends + semantic search           [dashboard/app.py]
+ "Ask AI" RAG-style Q&A grounded in your ticket data

Prefect [orchestration/pipeline_flow.py] wires all of the above into one
runnable, retryable DAG.
```

## 2. The AI components specifically

This project uses AI in **two distinct ways**, both common patterns in 2026:

1. **LLM-as-structured-data-extractor** (`enrichment/llm_enrich.py`): Claude
   reads unstructured ticket text and returns strict JSON — category,
   urgency, sentiment score, summary. This turns free text into queryable
   warehouse columns. Critically, the output is validated with Pandera
   (`validation/schemas.py`) before anything downstream trusts it — LLM
   output is treated as untrusted input, same as any external API response.

2. **Retrieval-augmented generation (RAG)** (`dashboard/app.py`,
   `enrichment/semantic_search.py`): a user's question is used to retrieve
   the most relevant tickets from the warehouse, and only those tickets are
   handed to Claude as context to answer from — instead of letting the model
   guess or hallucinate an answer with no grounding.

### About the embeddings/search layer

A real production RAG setup usually pairs Claude (generation) with a
dedicated embeddings model — **Voyage AI** (Anthropic's recommended
embeddings partner) or OpenAI embeddings — for true semantic vector search.
This project's sandbox network only allows package registries, not
embedding APIs, so `semantic_search.py` uses TF-IDF + cosine similarity as a
fully offline stand-in that demonstrates the identical retrieval pattern.
Swapping in real embeddings is a small, clearly marked change — see the
`get_embedder()` docstring in that file.

## 3. Mock mode vs. live mode

|                   | Mock mode (default)          | Live mode                                        |
| ----------------- | ---------------------------- | ------------------------------------------------ |
| Trigger           | No `ANTHROPIC_API_KEY` set   | `ANTHROPIC_API_KEY` set in environment           |
| Ticket enrichment | Keyword-based heuristic      | Real Claude classification/scoring/summarization |
| "Ask AI"          | Shows retrieved context only | Claude answers grounded in retrieved tickets     |
| Cost              | Free, fully offline          | Uses your Anthropic API credits                  |

This matters for a real reason: it's the same "mock external dependency in
CI, use the real one in production" pattern you'd want for any pipeline step
that costs money or needs network access, not just LLM calls.

## 4. Project structure

```
support-ai-analytics/
├── requirements.txt
├── pytest.ini
├── .env.example                  <- copy to .env to add your Claude API key
├── PROJECT_OVERVIEW.md            <- expanded project purpose and architecture guide
├── .gitignore
├── Dockerfile
├── .dockerignore
├── .vscode/
│   ├── settings.json              <- interpreter path, pytest config
│   ├── launch.json                <- 7 pre-built run/debug configs
│   └── extensions.json            <- recommended VS Code extensions
├── warehouse.duckdb               <- created after first run
├── data/
│   ├── raw/                       <- generated ticket + customer CSVs
│   └── processed/                 <- cleaned parquet + LLM enrichment output
├── ingestion/
│   ├── generate_raw_tickets.py    <- simulates a support-desk export
│   └── load_to_duckdb.py          <- loads validated data into DuckDB
├── enrichment/
│   ├── llm_enrich.py              <- Claude classification/scoring/summarization
│   └── semantic_search.py         <- TF-IDF retrieval (RAG's "R")
├── validation/
│   ├── schemas.py                 <- Pandera contracts, incl. LLM-output contract
│   └── validate_all.py
├── dbt_project/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── staging/               <- stg_customers, stg_tickets, stg_ticket_enrichment
│       └── marts/                 <- fct_tickets + 3 business-facing marts
├── orchestration/
│   └── pipeline_flow.py           <- Prefect flow tying it all together
├── dashboard/
│   └── app.py                     <- Streamlit dashboard incl. "Ask AI"
└── tests/
    ├── conftest.py
    ├── test_schemas.py             <- 9 tests: contracts reject bad data correctly
    ├── test_llm_enrich.py          <- 11 tests: enrichment logic + schema compliance
    ├── test_semantic_search.py     <- 4 tests: retrieval relevance and ranking
    └── test_pipeline_integration.py <- 8 tests: real end-to-end numeric correctness
```

## 5. Step-by-step: run it yourself

### Step 1 — Set up the environment

```bash
cd support-ai-analytics
python3 -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2 — Generate raw tickets

```bash
python ingestion/generate_raw_tickets.py
```

Creates 300 customers and 400 support tickets with real templated complaint
text across 5 categories (billing, bugs, account access, feature requests,
shipping).

### Step 3 — Run LLM enrichment

```bash
cd enrichment
python llm_enrich.py
cd ..
```

Without an API key, this runs in mock mode (prints `MOCK` in the output) and
uses a keyword heuristic. To use real Claude:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
cd enrichment && python llm_enrich.py && cd ..
```

You'll see `LIVE (Claude API)` printed, and each ticket gets genuine
LLM-based classification, urgency, sentiment, and summary.

### Step 4 — Validate everything (including the LLM's own output)

```bash
cd validation
python validate_all.py
cd ..
```

If Claude (or the mock) ever returned a category outside the allowed list,
or a sentiment score outside -1 to 1, this step catches it here — before it
reaches the warehouse.

### Step 5 — Load into DuckDB

```bash
python ingestion/load_to_duckdb.py
```

### Step 6 — Transform with dbt

```bash
cd dbt_project
dbt run --profiles-dir .
dbt test --profiles-dir .
cd ..
```

Builds `fct_tickets` plus three marts (daily trends, category breakdown,
plan health) and runs 20 automated tests — including tests that Claude's
`category` and `urgency` outputs match the allowed contract.

### Step 7 — Or run the whole thing as one orchestrated pipeline

```bash
python orchestration/pipeline_flow.py
```

Runs generate → enrich → validate → load → dbt run → dbt test as a single
retryable, logged Prefect flow.

### Step 8 — Launch the dashboard

```bash
streamlit run dashboard/app.py
```

Open the printed URL. You'll see:

- KPIs (ticket volume, average AI-scored sentiment, % high urgency)
- Volume and sentiment trends over time
- Category breakdown, colored by AI-scored sentiment
- Plan-level ticket health (which pricing tier generates the most negative
  sentiment)
- **Semantic search** — find tickets by meaning, not exact keywords
- **Ask AI** — ask a natural-language question; the app retrieves relevant
  tickets and (with a key set) has Claude answer grounded in them

## 6. Running it in Docker

```bash
docker build -t support-ai-analytics .
docker run -p 8501:8501 support-ai-analytics                       # mock mode
docker run -p 8501:8501 -e ANTHROPIC_API_KEY=sk-ant-... support-ai-analytics  # live mode
```

Note: the image builds its warehouse in mock mode at build time (no key
baked into the image, for security). If you run with a live key, re-run
`python orchestration/pipeline_flow.py` inside the running container to
re-enrich the tickets with real Claude output.

## 7. Running the test suite

A pytest suite in `tests/` verifies the pipeline produces **correct** output,
not just that it runs without crashing:

```bash
python -m pytest tests/ -v                    # all 33 tests
python -m pytest tests/ -m "not integration" -v   # fast unit tests only (~1s)
python -m pytest tests/test_pipeline_integration.py -v  # slower end-to-end checks (~7s)
```

What's covered:

- **`test_schemas.py`** (9 tests) — confirms the Pandera contracts actually
  reject bad data: duplicate IDs, null fields, an invalid category, an
  invalid urgency value, and an out-of-range sentiment score. A schema that
  never rejects anything isn't validating anything, so these tests check
  the _rejection_ path, not just the happy path.
- **`test_llm_enrich.py`** (11 tests) — checks the mock-mode enrichment logic
  classifies known ticket text into the right category, flags urgent language
  correctly, scores harsh language more negatively than neutral language, and
  that `enrich_tickets()`'s output always satisfies the enrichment schema.
- **`test_semantic_search.py`** (4 tests) — confirms search actually retrieves
  relevant tickets for a query (e.g. a billing-specific query ranks the
  billing ticket first) and that results are sorted correctly.
- **`test_pipeline_integration.py`** (8 tests) — runs the real pipeline
  end-to-end and checks the warehouse numbers are internally consistent:
  category counts sum to the total ticket count, no sentiment scores fall
  outside -1 to 1, no ticket is missing its AI-derived fields after the
  join, etc.

All 33 currently pass. If you add a live `ANTHROPIC_API_KEY`, re-run the
integration tests afterward — the mock-vs-live output will differ, but the
correctness checks (schema validity, sums matching totals, no out-of-range
values) should still all pass, since they're checking the _contract_, not
the exact wording.

## 8. What's data engineering vs. what's "AI engineering" here

- **Data engineering**: `ingestion/`, `validation/`, `orchestration/`, the
  `staging` dbt layer, Docker — building a reliable pipeline around the AI
  step so its output can be trusted.
- **AI engineering**: `enrichment/llm_enrich.py` (structured extraction with
  retries and a validated output contract) and the RAG loop in
  `dashboard/app.py` (retrieval + grounded generation).
- **Data analysis**: the `marts` dbt layer and the rest of the dashboard —
  turning AI-enriched data into decisions (e.g. "which plan generates the
  most negative sentiment tickets?").

## 9. Setting this up in Visual Studio Code

### Step 1 — Open the project

1. Unzip the project folder somewhere on your machine.
2. Open VS Code → **File → Open Folder...** → select the `support-ai-analytics` folder.
3. VS Code will detect the `.vscode/extensions.json` file and prompt you to
   install recommended extensions (Python, Pylance, dbt Power User, SQLTools,
   Docker). Click **Install All** — or install just the Python one if you
   want to keep it minimal.

### Step 2 — Create the virtual environment

Open a terminal in VS Code (**Terminal → New Terminal**, or `` Ctrl+` ``):

```bash
python3 -m venv venv
```

- **macOS/Linux**: `source venv/bin/activate`
- **Windows**: `venv\Scripts\activate`

### Step 3 — Select the interpreter

1. Press `Ctrl+Shift+P` (`Cmd+Shift+P` on Mac) → type **"Python: Select Interpreter"**.
2. Choose the one at `./venv/bin/python` (or `.\venv\Scripts\python.exe` on Windows).
   This is already set as the default in `.vscode/settings.json`, so VS Code
   should suggest it automatically.

### Step 4 — Install dependencies

In the same terminal (venv activated):

```bash
pip install -r requirements.txt
```

### Step 5 — (Optional) add your Claude API key

```bash
cp .env.example .env
```

Open `.env` and paste your key:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Skip this step entirely if you just want to run everything in mock mode.

The `.env` file is ignored by Git, so it is the recommended permanent
workspace-local configuration. Never commit it or paste the key into source
files. If a key has been exposed in a terminal transcript, chat, screenshot,
or repository, revoke it in the Anthropic console and create a replacement
before using live mode.

The pinned Anthropic SDK requires a compatible HTTP client. Install the full
dependency set after creating the environment so `httpx<0.28` is installed:

```bash
python -m pip install -r requirements.txt
```

### Step 6 — Run the pipeline

You have three ways to run things in VS Code:

**A. Using the integrated terminal** (simplest):

```bash
python orchestration/pipeline_flow.py
```

**B. Using the Run and Debug panel** (`Ctrl+Shift+D`):
The project ships with `.vscode/launch.json` containing 7 pre-configured
run profiles. Pick one from the dropdown at the top of the Run and Debug
panel and press the green ▶ play button:

- `1. Generate raw tickets`
- `2. LLM enrich`
- `3. Validate all`
- `4. Load to DuckDB`
- `5. Run full pipeline (Prefect)` ← runs everything in one go
- `6. Run pytest (all tests)`
- `7. Launch Streamlit dashboard`

This is the easiest way to set breakpoints and step through the code — e.g.
put a breakpoint inside `_mock_enrich()` in `enrichment/llm_enrich.py` and
run profile `2` to watch the classification logic execute line by line.

**C. Using the Testing panel** (flask icon on the left sidebar):
Since `python.testing.pytestEnabled` is set in `.vscode/settings.json`, VS
Code auto-discovers the pytest suite in `tests/`. Click the beaker/flask icon
in the left sidebar to see all 33 tests listed individually — click any one
to run just that test, or click the play button at the top to run them all.

### Step 7 — View the dashboard

After running the pipeline once (any of the methods above), launch:

```bash
streamlit run dashboard/app.py
```

VS Code will show a notification with a clickable `localhost` link, or open
it manually in your browser.

To verify the dashboard without making Claude API calls, start it with the
key unset:

```bash
env -u ANTHROPIC_API_KEY streamlit run dashboard/app.py
```

The dashboard will still provide KPIs, charts, and semantic search. The
**Ask AI** section will display retrieved ticket context until a valid key is
configured.

### Troubleshooting

- **"dbt: command not found"** — make sure your venv is activated in the
  terminal you're running commands from; VS Code's integrated terminal
  should auto-activate it, but double check with `which python` (should
  point inside `venv/`).
- **Import errors in `enrichment/llm_enrich.py` when opened directly** —
  this file expects to be run from inside the `enrichment/` folder (or via
  the provided launch configs, which set the correct working directory).
  Running it from the repo root will fail on `from schemas import ...`.
- **Pylance underlines `from schemas import ...` in red** — this is just a
  static-analysis warning, not a runtime error; `.vscode/settings.json`
  already adds `enrichment/` and `validation/` to Pylance's search paths to
  minimize this, but a stray warning here or there is harmless.

## 10. Natural next steps if you want to extend this

- Swap TF-IDF for real embeddings (Voyage AI or OpenAI) for genuine semantic
  search — see the `get_embedder()` note in `semantic_search.py`.
- Add a **prompt-caching** or **batch API** step to cut Claude API costs when
  enriching large ticket volumes.
- Add an **eval script** comparing Claude's `category` output against the
  `true_category` column kept in the raw ticket generator, to quantify
  classification accuracy.
- Swap DuckDB for **Snowflake/BigQuery/Postgres** in production — only the
  dbt profile changes.
- Add a **human-in-the-loop review queue** in the dashboard for
  low-confidence or high-urgency AI classifications before they're acted on.

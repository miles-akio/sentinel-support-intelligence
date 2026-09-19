FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Build the warehouse at image build time so the dashboard has data on
# first boot. Runs in MOCK mode by default (no key baked into the image
# for security reasons) — pass ANTHROPIC_API_KEY at `docker run` time to
# use live Claude calls instead; re-run the pipeline inside the container
# afterward to re-enrich with real LLM output.
RUN python ingestion/generate_raw_tickets.py \
    && cd enrichment && python llm_enrich.py && cd .. \
    && cd validation && python validate_all.py && cd .. \
    && python ingestion/load_to_duckdb.py \
    && cd dbt_project && dbt run --profiles-dir . && cd ..

EXPOSE 8501

CMD ["streamlit", "run", "dashboard/app.py", "--server.address=0.0.0.0", "--server.port=8501"]

"""
load_to_duckdb.py
------------------
Loads validated raw tables AND the validated LLM enrichment output into
DuckDB. Note the enrichment table sits in `raw` alongside the source data —
from dbt's perspective, an LLM's structured output is just another upstream
source to join against, no different from a third-party API extract.
"""

from pathlib import Path

import duckdb

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DB_PATH = BASE_DIR / "warehouse.duckdb"

if __name__ == "__main__":
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw;")

    for table, filename in [
        ("customers", "customers.parquet"),
        ("tickets", "tickets.parquet"),
        ("ticket_enrichment", "ticket_enrichment.parquet"),
    ]:
        con.execute(
            f"""
            CREATE OR REPLACE TABLE raw.{table} AS
            SELECT * FROM read_parquet('{PROCESSED_DIR / filename}');
            """
        )
        count = con.execute(f"SELECT COUNT(*) FROM raw.{table}").fetchone()[0]
        print(f"raw.{table}: {count} rows loaded")

    con.close()
    print(f"\nDuckDB warehouse ready at: {DB_PATH}")

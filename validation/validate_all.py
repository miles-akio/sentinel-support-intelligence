"""
validate_all.py
-----------------
Validates the raw ticket/customer data AND the LLM enrichment output against
the Pandera contracts in schemas.py. If Claude (or the mock fallback) ever
returns something outside the allowed contract, this step fails loudly
rather than letting bad data reach the warehouse.
"""

import sys
from pathlib import Path

import polars as pl

from schemas import tickets_schema, customers_schema, enrichment_schema

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def run() -> int:
    customers = pl.read_csv(RAW_DIR / "customers.csv")
    tickets = pl.read_csv(RAW_DIR / "tickets.csv").drop("true_category")  # drop the eval-only ground-truth column
    enrichment = pl.read_parquet(PROCESSED_DIR / "ticket_enrichment.parquet")

    try:
        customers_schema.validate(customers.to_pandas())
        tickets_schema.validate(tickets.to_pandas())
        enrichment_schema.validate(enrichment.to_pandas())
    except Exception as e:
        print("VALIDATION FAILED:")
        print(e)
        return 1

    # Persist the validated, ticket-shaped inputs as clean parquet for loading.
    customers.write_parquet(PROCESSED_DIR / "customers.parquet")
    tickets.write_parquet(PROCESSED_DIR / "tickets.parquet")

    print("Validation passed.")
    print(f"  customers  -> {customers.shape}")
    print(f"  tickets    -> {tickets.shape}")
    print(f"  enrichment -> {enrichment.shape}")
    return 0


if __name__ == "__main__":
    sys.exit(run())

"""
test_pipeline_integration.py
------------------------------
These tests run the actual pipeline scripts (in mock mode) end-to-end and
then check the DuckDB warehouse for CORRECT output — not just "did it run
without crashing," but "do the numbers actually add up."

This is slower than the unit tests above (it runs the real generate ->
enrich -> validate -> load -> dbt sequence), so it's marked separately and
can be skipped with `pytest -m "not integration"` if you just want the
fast unit tests during development.
"""

import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
VENV_PY = sys.executable
DBT_DIR = BASE_DIR / "dbt_project"


def _run(cmd, cwd=None):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    assert result.returncode == 0, f"Command failed: {' '.join(cmd)}\n{result.stderr}"
    return result


@pytest.fixture(scope="module")
def built_warehouse():
    """Runs the full pipeline once and yields a connection to the resulting warehouse."""
    _run([VENV_PY, str(BASE_DIR / "ingestion" / "generate_raw_tickets.py")])
    _run([VENV_PY, "llm_enrich.py"], cwd=BASE_DIR / "enrichment")
    _run([VENV_PY, "validate_all.py"], cwd=BASE_DIR / "validation")
    _run([VENV_PY, str(BASE_DIR / "ingestion" / "load_to_duckdb.py")])

    dbt_bin = str(Path(VENV_PY).parent / "dbt")
    _run([dbt_bin, "run", "--profiles-dir", "."], cwd=DBT_DIR)
    _run([dbt_bin, "test", "--profiles-dir", "."], cwd=DBT_DIR)

    con = duckdb.connect(str(BASE_DIR / "warehouse.duckdb"), read_only=True)
    yield con
    con.close()


@pytest.mark.integration
def test_all_expected_tables_exist(built_warehouse):
    tables = {row[0] for row in built_warehouse.execute("SHOW TABLES").fetchall()}
    expected = {
        "fct_tickets",
        "mart_daily_ticket_trends",
        "mart_category_breakdown",
        "mart_plan_health",
    }
    assert expected.issubset(tables)


@pytest.mark.integration
def test_fct_tickets_row_count_matches_generated_tickets(built_warehouse):
    fct_count = built_warehouse.execute("SELECT COUNT(*) FROM fct_tickets").fetchone()[0]
    raw_count = built_warehouse.execute("SELECT COUNT(*) FROM raw.tickets").fetchone()[0]
    assert fct_count == raw_count == 400


@pytest.mark.integration
def test_category_breakdown_sums_to_total_tickets(built_warehouse):
    """Every ticket must land in exactly one category — the mart's counts must sum to the total."""
    total = built_warehouse.execute("SELECT COUNT(*) FROM fct_tickets").fetchone()[0]
    category_sum = built_warehouse.execute("SELECT SUM(num_tickets) FROM mart_category_breakdown").fetchone()[0]
    assert category_sum == total


@pytest.mark.integration
def test_daily_trends_sums_to_total_tickets(built_warehouse):
    total = built_warehouse.execute("SELECT COUNT(*) FROM fct_tickets").fetchone()[0]
    daily_sum = built_warehouse.execute("SELECT SUM(num_tickets) FROM mart_daily_ticket_trends").fetchone()[0]
    assert daily_sum == total


@pytest.mark.integration
def test_all_sentiment_scores_within_valid_range(built_warehouse):
    out_of_range = built_warehouse.execute(
        "SELECT COUNT(*) FROM fct_tickets WHERE sentiment_score < -1.0 OR sentiment_score > 1.0"
    ).fetchone()[0]
    assert out_of_range == 0


@pytest.mark.integration
def test_all_categories_are_in_allowed_set(built_warehouse):
    allowed = {"billing", "bug", "account_access", "feature_request", "shipping", "other"}
    rows = built_warehouse.execute("SELECT DISTINCT category FROM fct_tickets").fetchall()
    found = {r[0] for r in rows}
    assert found.issubset(allowed)


@pytest.mark.integration
def test_no_null_categories_or_urgency_after_join(built_warehouse):
    """Guards against a silent LEFT JOIN mismatch between tickets and enrichment."""
    nulls = built_warehouse.execute(
        "SELECT COUNT(*) FROM fct_tickets WHERE category IS NULL OR urgency IS NULL"
    ).fetchone()[0]
    assert nulls == 0


@pytest.mark.integration
def test_plan_health_covers_all_plans_present_in_customers(built_warehouse):
    customer_plans = {r[0] for r in built_warehouse.execute("SELECT DISTINCT plan FROM raw.customers").fetchall()}
    mart_plans = {r[0] for r in built_warehouse.execute("SELECT DISTINCT plan FROM mart_plan_health").fetchall()}
    assert customer_plans == mart_plans

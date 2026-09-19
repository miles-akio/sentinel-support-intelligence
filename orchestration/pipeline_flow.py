"""
pipeline_flow.py
-----------------
Orchestrates the full AI + analytics pipeline as one retryable DAG:

    generate raw tickets/customers
            |
            v
    LLM enrichment (Claude API, or mock fallback)   <- the AI step
            |
            v
    validate raw data AND LLM output (Pandera)      <- trust-but-verify gate
            |
            v
    load into DuckDB
            |
            v
    dbt run (staging -> marts)
            |
            v
    dbt test (including LLM-output contract tests)

Run locally:
    python orchestration/pipeline_flow.py

To use live Claude calls instead of the offline mock, set your key first:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python orchestration/pipeline_flow.py
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from prefect import flow, task

BASE_DIR = Path(__file__).resolve().parent.parent


def _resolve_local_bin(binary_name: str) -> str:
    for venv_dir in (BASE_DIR / ".venv", BASE_DIR / "venv"):
        candidate = venv_dir / "bin" / binary_name
        if candidate.exists():
            return str(candidate)

    resolved = shutil.which(binary_name)
    if resolved:
        return resolved

    raise FileNotFoundError(f"Could not find {binary_name} in the local virtual environment or PATH.")


VENV_PY = Path(_resolve_local_bin("python"))
DBT_BIN = Path(_resolve_local_bin("dbt"))
DBT_DIR = BASE_DIR / "dbt_project"


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=os.environ.copy())
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")


@task(retries=1, log_prints=True)
def generate_raw_data():
    _run([str(VENV_PY), str(BASE_DIR / "ingestion" / "generate_raw_tickets.py")])


@task(retries=2, log_prints=True)
def llm_enrich():
    _run([str(VENV_PY), "llm_enrich.py"], cwd=BASE_DIR / "enrichment")


@task(retries=0, log_prints=True)
def validate_all():
    _run([str(VENV_PY), "validate_all.py"], cwd=BASE_DIR / "validation")


@task(retries=1, log_prints=True)
def load_to_duckdb():
    _run([str(VENV_PY), str(BASE_DIR / "ingestion" / "load_to_duckdb.py")])


@task(retries=1, log_prints=True)
def dbt_run():
    _run([str(DBT_BIN), "run", "--profiles-dir", "."], cwd=DBT_DIR)


@task(retries=0, log_prints=True)
def dbt_test():
    _run([str(DBT_BIN), "test", "--profiles-dir", "."], cwd=DBT_DIR)


@flow(name="support-ai-analytics-pipeline", log_prints=True)
def support_ai_pipeline():
    generate_raw_data()
    llm_enrich()
    validate_all()
    load_to_duckdb()
    dbt_run()
    dbt_test()
    print("Pipeline completed successfully. Warehouse is ready for the dashboard.")


if __name__ == "__main__":
    support_ai_pipeline()

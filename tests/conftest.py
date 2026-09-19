"""
conftest.py
------------
Shared pytest fixtures. Adds the enrichment/ and validation/ folders to
sys.path so their modules (which use simple `from schemas import ...`
style imports, matching how they're run as standalone pipeline scripts)
can be imported directly in tests without restructuring the project into
a formal Python package.
"""

import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "enrichment"))
sys.path.insert(0, str(BASE_DIR / "validation"))


@pytest.fixture(scope="session")
def base_dir() -> Path:
    return BASE_DIR

"""Loads the real files into a disposable database for the API tests."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import psycopg
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DSN = os.environ.get("TEST_DATABASE_URL")


def load_pipeline():
    pipeline_dir = REPO_ROOT / "pipeline"
    sys.path.insert(0, str(pipeline_dir))
    spec = importlib.util.spec_from_file_location("pipeline_run", pipeline_dir / "run.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["pipeline_run"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def database():
    if not DSN:
        pytest.skip("TEST_DATABASE_URL is not set")
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
    pipeline = load_pipeline()
    pipeline.run(DSN, pipeline.DEFAULT_INCOMING, pipeline.DEFAULT_MACHINE_LIST)
    os.environ["DATABASE_URL"] = DSN
    return DSN

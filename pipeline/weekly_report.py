"""Publish the weekly summary report (the brief's stretch goal).

Usage:
    python pipeline/weekly_report.py           # skipped if this week's figures haven't changed
    python pipeline/weekly_report.py --force   # write the commentary again

It runs every Monday at 07:00 SAST, after the 04:00 load has delivered Sunday's events. The
report covers the latest Monday-to-Sunday week in the data. It shares its queries, LLM client
and figure check with the API, so it needs app/api/requirements.txt.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app" / "api"))

from llm import OpenRouterClient  # noqa: E402
from report import publish_report  # noqa: E402

from run import apply_schema  # noqa: E402

log = logging.getLogger("weekly_report")


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish the weekly summary report.")
    parser.add_argument("--force", action="store_true", help="write the commentary again")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # Quieten the HTTP client, because the only thing it adds is a line per model call.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        log.error(json.dumps({"event": "report_failed", "error": "DATABASE_URL is not set"}))
        return 2

    with psycopg.connect(dsn, row_factory=dict_row, autocommit=True) as conn:
        with conn.transaction():
            apply_schema(conn)
        outcome = publish_report(conn, OpenRouterClient(), args.force)

    log.info(json.dumps({"event": "report_finished", "outcome": outcome}))
    # A Monday with nothing to report needs someone's attention, so the run shows as failed.
    return 1 if outcome == "no_data" else 0


if __name__ == "__main__":
    sys.exit(main())

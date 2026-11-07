"""Database connections for the API. Every connection is read-only."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

STATEMENT_TIMEOUT_MS = 5000


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    """Open a short-lived read-only connection.

    Serverless instances come and go, so each request opens its own connection and
    relies on Neon's pooler. prepare_threshold=None keeps it compatible with that pooler.
    The read-only session is a second layer on top of the read-only database role.
    SET LOCAL lasts for this transaction only, because the pooler shares server sessions.
    """
    dsn = os.environ["DATABASE_URL"]
    with psycopg.connect(dsn, row_factory=dict_row, prepare_threshold=None) as conn:
        conn.read_only = True
        conn.execute(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}")
        yield conn

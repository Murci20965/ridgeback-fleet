"""A database outage gives a clear, quick error. These tests need no database."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import main

# Nothing listens on port 1, so the connection is refused straight away.
UNREACHABLE = "postgresql://nobody:nothing@127.0.0.1:1/none"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", UNREACHABLE)
    monkeypatch.setattr(main, "limiter", main.RateLimiter(100, 60))
    return TestClient(main.app)


def test_dashboard_reports_the_outage(client):
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 503
    assert response.json() == {"detail": "Fleet data is unavailable."}


def test_chat_ends_with_a_friendly_error(client):
    response = client.post("/api/v1/chat", json={"question": "Hello"})
    event = json.loads(response.text.strip().splitlines()[-1])
    assert event == {
        "type": "error",
        "message": "Couldn't read the fleet data. Try again shortly.",
    }
    assert UNREACHABLE not in response.text

"""The Ridgeback API: dashboard data and the chat. All routes sit under /api/v1."""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import Iterator
from datetime import date

import psycopg
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

import db
import queries
from agent import answer_question
from dashboard import DateOutsideData, build_dashboard
from llm import OpenRouterClient
from schemas import Branch, ChatRequest, Dashboard, MachineType, WeeklyReport

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("api")

RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60.0


class RateLimiter:
    """Limits questions per IP within one server instance.

    It isn't shared across instances, so it slows casual abuse rather than guaranteeing
    a global limit. OpenRouter's spending cap on the key is the hard backstop for cost.
    """

    def __init__(self, limit: int, window: float) -> None:
        self.limit = limit
        self.window = window
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self.lock:
            hits = self.hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True


limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS)
router = APIRouter(prefix="/api/v1")


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/dashboard", response_model=Dashboard)
def dashboard(
    day: date | None = Query(None, description="A single day. Leave out for the latest week."),
    machine_type: MachineType | None = None,
    branch: Branch | None = None,
) -> Dashboard:
    try:
        with db.connect() as conn:
            return build_dashboard(conn, day, machine_type, branch)
    except DateOutsideData as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except psycopg.Error as exc:
        log.exception(json.dumps({"event": "dashboard_error", "detail": type(exc).__name__}))
        raise HTTPException(status_code=503, detail="Fleet data is unavailable.") from exc


@router.get("/reports/latest", response_model=WeeklyReport)
def latest_report() -> WeeklyReport:
    try:
        with db.connect() as conn:
            report = queries.get_latest_report(conn)
    except psycopg.errors.UndefinedTable:
        # The pipeline creates the table the first time it publishes a report.
        report = None
    except psycopg.Error as exc:
        log.exception(json.dumps({"event": "report_error", "detail": type(exc).__name__}))
        raise HTTPException(status_code=503, detail="The report is unavailable.") from exc
    if report is None:
        raise HTTPException(status_code=404, detail="No report has been published yet.")
    return report


@router.post("/chat")
def chat(body: ChatRequest, request: Request) -> StreamingResponse:
    """Streams newline-delimited JSON: `status` updates, then one `answer` or `error`."""
    if not limiter.allow(client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many questions. Try again in a minute.")

    def stream() -> Iterator[str]:
        try:
            with db.connect() as conn:
                events = answer_question(conn, OpenRouterClient(), body.question, body.history)
                for event in events:
                    yield json.dumps(event, default=str) + "\n"
        except (psycopg.Error, KeyError) as exc:
            log.exception(json.dumps({"event": "chat_error", "detail": type(exc).__name__}))
            message = "Couldn't read the fleet data. Try again shortly."
            yield json.dumps({"type": "error", "message": message}) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


app = FastAPI(
    title="Ridgeback Fleet API",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
)
app.include_router(router)

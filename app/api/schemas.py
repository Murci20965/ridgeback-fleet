"""The API contract. FastAPI publishes these as OpenAPI at /api/v1/docs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

MachineType = Literal["Forklift", "Reach Truck", "PPT"]
Branch = Literal["Airport", "Harbour", "Northgate", "Riverside"]


class Coverage(BaseModel):
    first_date: date
    last_date: date
    days_with_data: int
    week_start: date
    week_end: date


class Kpis(BaseModel):
    run_hours: float
    active_machines: int
    fleet_size: int
    impacts: int
    harsh_events: int
    idle_events: int
    unattributed_impacts: int


class AttentionItem(BaseModel):
    severity: Literal["critical", "warning"]
    kind: str
    title: str
    detail: str
    question: str


class MachineRow(BaseModel):
    ref_no: str
    machine_type: MachineType
    assigned_branch: str
    reported_branches: list[str]
    run_hours: float
    active: bool


class DriverRow(BaseModel):
    driver_name: str | None
    impacts: int
    harsh: int
    idle: int
    safety_total: int


class BranchRow(BaseModel):
    branch: str
    run_hours: float
    active_machines: int
    impacts: int
    harsh: int


class DailySummary(BaseModel):
    event_date: date
    run_hours: float
    active_machines: int
    impacts: int
    harsh_events: int


class DailyBranchHours(BaseModel):
    event_date: date
    branch: str
    run_hours: float


class PipelineStatus(BaseModel):
    last_run_at: datetime
    files: int
    files_failed: int
    files_partial: int
    rows_total: int
    rows_loaded: int
    rows_rejected: int
    rows_duplicate: int


class Dashboard(BaseModel):
    coverage: Coverage | None
    from_date: date | None = None
    to_date: date | None = None
    headline: str | None = None
    kpis: Kpis | None = None
    attention: list[AttentionItem] = []
    machines: list[MachineRow] = []
    drivers: list[DriverRow] = []
    branches: list[BranchRow] = []
    daily: list[DailySummary] = []
    daily_branch_hours: list[DailyBranchHours] = []
    pipeline: PipelineStatus | None = None


class Commentary(BaseModel):
    """What the LLM writes for the weekly report. The figures never come from here."""

    summary: str = Field(min_length=1, max_length=800)
    highlights: list[str] = Field(min_length=1, max_length=5)
    checks: list[str] = Field(max_length=5)


class ReportFacts(BaseModel):
    """The figures in a weekly report, stored as they were when it was written."""

    week_start: date
    week_end: date
    days_with_data: int
    headline: str
    kpis: Kpis
    branches: list[BranchRow]
    daily: list[DailySummary]
    top_machines: list[MachineRow]
    least_used_machines: list[MachineRow]
    inactive_machines: list[MachineRow]
    top_drivers: list[DriverRow]
    attention: list[AttentionItem]
    pipeline: PipelineStatus | None


class WeeklyReport(BaseModel):
    week_start: date
    week_end: date
    generated_at: datetime
    facts: ReportFacts
    commentary: Commentary | None
    model: str | None


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    history: list[ChatTurn] = Field(default=[], max_length=20)

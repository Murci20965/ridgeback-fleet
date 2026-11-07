"""Cleaning rules for the daily telemetry files (Task 1).

Everything here is pure: no database and no file system. A file's text goes in,
and clean events plus reasoned rejections come out. That keeps each rule easy to
unit test, and lets the pipeline and the tests share a single implementation.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field

EVENT_TYPES = (
    "Power Up",
    "Driver Change",
    "Unit (Time/GPS) Update Level",
    "Impact",
    "Harsh Braking",
    "Harsh Acceleration",
    "Speeding",
    "Excess Idle",
)

# Canonical field name -> header spellings seen after normalise_header().
COLUMN_ALIASES = {
    "occurred_at": {"dateandtime"},
    "ref_no": {"refno"},
    "branch": {"branchname"},
    "event_type": {"txflagstrings"},
    "run_seconds": {"runhours"},
    "driver_name": {"drivername"},
    "driver_surname": {"driversurname"},
}

FILE_NAME_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})_DailyTelemetryData\.csv$")
BRANCH_PREFIX = "ridgeback "

# The provider can resend old rows (the 9 Sep file holds rows from 7 Sep), so a
# row may be up to this many days older than the delivery date.
MAX_LATE_DAYS = 7

# A fall in RunHours larger than this is a meter reset, not a late reading.
# Late rows at a shift change differ by minutes; the two real resets fall by hours.
RESET_THRESHOLD_SECONDS = 3600

_TIMESTAMP_FORMATS = (
    (re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$"), "%Y-%m-%dT%H:%M:%S"),
    (re.compile(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}$"), "%d/%m/%Y %H:%M:%S"),
)


class FileRejected(Exception):
    """The whole file is unusable, for example because a required column is missing."""


class RowRejected(Exception):
    """One row is unusable. `reason` is a stable code stored with the raw row."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(detail or reason)
        self.reason = reason
        self.detail = detail


class CleanEvent(BaseModel):
    """A validated telemetry row, ready to load."""

    model_config = ConfigDict(frozen=True)

    event_key: str
    occurred_at: datetime
    ref_no: str = Field(min_length=1)
    reported_branch: str = Field(min_length=1)
    event_type: str
    run_seconds: int = Field(ge=0)
    driver_key: str | None = None
    driver_name: str | None = None
    source_line: int = Field(ge=1)

    @property
    def event_date(self) -> date:
        """The day the event happened, which is never the file's delivery date."""
        return self.occurred_at.date()


@dataclass(frozen=True)
class Rejection:
    line_no: int
    reason: str
    detail: str
    raw: str


@dataclass(frozen=True)
class CleanResult:
    delivery_date: date
    total_rows: int
    events: list[CleanEvent]
    rejections: list[Rejection]

    @property
    def is_partial(self) -> bool:
        """True when a structurally broken row suggests part of the file is missing."""
        return any(r.reason == "malformed_row" for r in self.rejections)


def collapse_spaces(value: str) -> str:
    return " ".join(value.split())


def normalise_header(value: str) -> str:
    """`Ref No`, `RefNo.` and ` refno ` all become `refno`."""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def delivery_date_from_name(file_name: str) -> date:
    match = FILE_NAME_PATTERN.match(file_name)
    if not match:
        raise FileRejected(f"file name doesn't match the expected pattern: {file_name}")
    try:
        return date.fromisoformat(match.group(1))
    except ValueError as exc:
        raise FileRejected(f"file name has an invalid date: {file_name}") from exc


def parse_timestamp(raw: str, delivery: date) -> datetime:
    """Parse a known format, then check the result is plausible for this delivery.

    The check is what stops 10/09/2026 being read as 9 October: a date outside
    the delivery window is rejected rather than quietly loaded on the wrong day.
    """
    value = raw.strip()
    for pattern, fmt in _TIMESTAMP_FORMATS:
        if pattern.match(value):
            try:
                parsed = datetime.strptime(value, fmt)
            except ValueError as exc:
                raise RowRejected("invalid_timestamp", value) from exc
            earliest = delivery - timedelta(days=MAX_LATE_DAYS)
            if not earliest <= parsed.date() < delivery:
                raise RowRejected("timestamp_out_of_range", value)
            return parsed
    raise RowRejected("invalid_timestamp", value)


def parse_branch(raw: str, known_branches: dict[str, str]) -> str:
    """Handle case, spacing and the `Ridgeback ` prefix. Keys are lower case."""
    value = collapse_spaces(raw).lower()
    if value.startswith(BRANCH_PREFIX):
        value = value[len(BRANCH_PREFIX) :]
    branch = known_branches.get(value)
    if branch is None:
        raise RowRejected("unknown_branch", raw)
    return branch


def parse_driver(name: str, surname: str) -> tuple[str | None, str | None]:
    """Return (identity key, display name). A blank driver stays blank, never guessed."""
    full_name = collapse_spaces(f"{name} {surname}")
    if not full_name:
        return None, None
    return full_name.casefold(), full_name.title()


def make_event_key(
    occurred_at: datetime, ref_no: str, event_type: str, run_seconds: int, driver_key: str | None
) -> str:
    """Identify an event by what it is, so the same event gets one key in any file."""
    parts = (occurred_at.isoformat(), ref_no, event_type, str(run_seconds), driver_key or "")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def map_columns(header: Sequence[str]) -> dict[str, int]:
    """Map fields to positions by name, because column order changes between files."""
    positions = {normalise_header(name): index for index, name in enumerate(header)}
    mapping: dict[str, int] = {}
    missing: list[str] = []
    for field_name, aliases in COLUMN_ALIASES.items():
        found = next((positions[alias] for alias in aliases if alias in positions), None)
        if found is None:
            missing.append(field_name)
        else:
            mapping[field_name] = found
    if missing:
        raise FileRejected(f"missing required columns: {', '.join(missing)}")
    return mapping


def clean_row(
    cells: Sequence[str],
    columns: dict[str, int],
    line_no: int,
    delivery: date,
    machines: set[str],
    known_branches: dict[str, str],
) -> CleanEvent:
    """Turn one raw row into a CleanEvent, or raise RowRejected with a reason."""
    occurred_at = parse_timestamp(cells[columns["occurred_at"]], delivery)

    ref_no = cells[columns["ref_no"]].strip()
    if not ref_no:
        raise RowRejected("missing_machine")
    if ref_no not in machines:
        raise RowRejected("unknown_machine", ref_no)

    branch = parse_branch(cells[columns["branch"]], known_branches)

    event_type = cells[columns["event_type"]].strip()
    if event_type not in EVENT_TYPES:
        raise RowRejected("unknown_event_type", event_type)

    run_text = cells[columns["run_seconds"]].strip()
    if not run_text.isdecimal():
        raise RowRejected("invalid_run_hours", run_text)
    run_seconds = int(run_text)

    driver_key, driver_name = parse_driver(
        cells[columns["driver_name"]], cells[columns["driver_surname"]]
    )

    return CleanEvent(
        event_key=make_event_key(occurred_at, ref_no, event_type, run_seconds, driver_key),
        occurred_at=occurred_at,
        ref_no=ref_no,
        reported_branch=branch,
        event_type=event_type,
        run_seconds=run_seconds,
        driver_key=driver_key,
        driver_name=driver_name,
        source_line=line_no,
    )


def clean_file(
    file_name: str, text: str, machines: set[str], known_branches: dict[str, str]
) -> CleanResult:
    """Clean one file. Every non-blank data row ends as an event or a rejection."""
    delivery = delivery_date_from_name(file_name)
    rows = csv.reader(io.StringIO(text))
    header = next(rows, None)
    if not header:
        raise FileRejected("file is empty")
    columns = map_columns(header)
    normalised_header = [normalise_header(cell) for cell in header]

    events: list[CleanEvent] = []
    rejections: list[Rejection] = []
    seen_keys: set[str] = set()
    total_rows = 0

    for cells in rows:
        if not cells:
            continue
        total_rows += 1
        line_no = rows.line_num
        raw = ",".join(cells)
        try:
            if [normalise_header(cell) for cell in cells] == normalised_header:
                raise RowRejected("repeated_header")
            if len(cells) != len(header):
                raise RowRejected(
                    "malformed_row", f"expected {len(header)} columns, got {len(cells)}"
                )
            event = clean_row(cells, columns, line_no, delivery, machines, known_branches)
            if event.event_key in seen_keys:
                raise RowRejected("duplicate_in_file")
        except RowRejected as rejected:
            rejections.append(Rejection(line_no, rejected.reason, rejected.detail, raw))
            continue
        seen_keys.add(event.event_key)
        events.append(event)

    if total_rows and not events:
        raise FileRejected(f"none of the {total_rows} rows were usable")
    return CleanResult(delivery, total_rows, events, rejections)


def split_into_segments(readings: Iterable[int]) -> list[list[int]]:
    """Split one machine's day of RunHours readings wherever the meter was reset.

    `readings` are in time order. Each returned segment is a run of readings from
    the same meter, so `run_seconds_for_day` can take max minus min per segment.

    Example: [100, 200, 150, 90000, 40, 60] -> [[100, 200, 150, 90000], [40, 60]]
    The fall from 200 to 150 is a late reading, while 90000 to 40 is a reset.
    Use RESET_THRESHOLD_SECONDS to tell them apart.
    """
    segments: list[list[int]] = []
    previous: int | None = None
    for reading in readings:
        is_reset = previous is not None and previous - reading > RESET_THRESHOLD_SECONDS
        if previous is None or is_reset:
            segments.append([])
        segments[-1].append(reading)
        previous = reading
    return segments


def run_seconds_for_day(readings: Iterable[int]) -> int:
    """Seconds a machine ran on one day: the sum of (max - min) across its segments."""
    return sum(max(segment) - min(segment) for segment in split_into_segments(readings))

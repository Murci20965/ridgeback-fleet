-- Ridgeback fleet data model. Safe to run repeatedly.
-- Times are local SAST. South Africa has no daylight saving, so a plain timestamp is
-- unambiguous, and event_date is the local day an operations manager means by "Tuesday".

CREATE TABLE IF NOT EXISTS branches (
    id   SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS machines (
    ref_no             TEXT PRIMARY KEY,
    machine_type       TEXT NOT NULL CHECK (machine_type IN ('Forklift', 'Reach Truck', 'PPT')),
    assigned_branch_id SMALLINT NOT NULL REFERENCES branches (id)
);

-- The files carry no driver ID, so identity is the normalised full name.
CREATE TABLE IF NOT EXISTS drivers (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    driver_key   TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS event_types (
    name            TEXT PRIMARY KEY,
    category        TEXT NOT NULL CHECK (category IN ('activity', 'routine', 'safety', 'idle')),
    counts_as_event BOOLEAN NOT NULL
);

INSERT INTO event_types (name, category, counts_as_event) VALUES
    ('Power Up', 'activity', TRUE),
    ('Driver Change', 'activity', TRUE),
    ('Unit (Time/GPS) Update Level', 'routine', FALSE),
    ('Impact', 'safety', TRUE),
    ('Harsh Braking', 'safety', TRUE),
    ('Harsh Acceleration', 'safety', TRUE),
    ('Speeding', 'safety', TRUE),
    ('Excess Idle', 'idle', TRUE)
ON CONFLICT (name) DO NOTHING;

-- event_key is a hash of what the event is, so a row resent in a later file can't load twice.
CREATE TABLE IF NOT EXISTS telemetry_events (
    event_key          CHAR(64) PRIMARY KEY,
    occurred_at        TIMESTAMP NOT NULL,
    event_date         DATE GENERATED ALWAYS AS (occurred_at::date) STORED,
    ref_no             TEXT NOT NULL REFERENCES machines (ref_no),
    reported_branch_id SMALLINT NOT NULL REFERENCES branches (id),
    event_type         TEXT NOT NULL REFERENCES event_types (name),
    run_seconds        BIGINT NOT NULL CHECK (run_seconds >= 0),
    driver_id          INTEGER REFERENCES drivers (id),
    source_file        TEXT NOT NULL,
    source_line        INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS telemetry_events_machine_day_idx
    ON telemetry_events (ref_no, event_date, occurred_at);
CREATE INDEX IF NOT EXISTS telemetry_events_day_type_idx
    ON telemetry_events (event_date, event_type);
CREATE INDEX IF NOT EXISTS telemetry_events_driver_idx
    ON telemetry_events (driver_id);
CREATE INDEX IF NOT EXISTS telemetry_events_source_file_idx
    ON telemetry_events (source_file);

CREATE TABLE IF NOT EXISTS rejected_rows (
    source_file TEXT NOT NULL,
    line_no     INTEGER NOT NULL,
    reason      TEXT NOT NULL,
    detail      TEXT NOT NULL DEFAULT '',
    raw         TEXT NOT NULL,
    PRIMARY KEY (source_file, line_no, reason)
);

-- One row per attempt on a file. Reruns add a row; they never change the data above.
CREATE TABLE IF NOT EXISTS ingest_runs (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    file_name      TEXT NOT NULL,
    checksum       CHAR(64),
    started_at     TIMESTAMPTZ NOT NULL,
    finished_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    outcome        TEXT NOT NULL CHECK (outcome IN ('success', 'partial', 'failed')),
    rows_total     INTEGER NOT NULL DEFAULT 0,
    rows_loaded    INTEGER NOT NULL DEFAULT 0,
    rows_rejected  INTEGER NOT NULL DEFAULT 0,
    rows_duplicate INTEGER NOT NULL DEFAULT 0,
    error          TEXT
);

CREATE INDEX IF NOT EXISTS ingest_runs_file_idx ON ingest_runs (file_name, id DESC);

-- One row per week, so reruns can't duplicate a report. The figures are stored as they were when
-- the report was written, because it's a record. Commentary is empty if the LLM couldn't write
-- text that passed the figure check.
CREATE TABLE IF NOT EXISTS weekly_reports (
    week_start       DATE PRIMARY KEY,
    week_end         DATE NOT NULL,
    generated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    facts            JSONB NOT NULL,
    facts_checksum   CHAR(64) NOT NULL,
    commentary       JSONB,
    commentary_model TEXT
);

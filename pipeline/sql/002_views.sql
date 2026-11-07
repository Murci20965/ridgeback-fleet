-- Reporting views. The dashboard and the chat both read these, so they can't disagree.

-- Hours per machine per day. A fall of more than 3600 seconds in RunHours is a meter reset
-- and starts a new segment; hours are the sum of (max - min) across segments. This mirrors
-- split_into_segments() in clean.py, and the integration tests compare the two.
CREATE OR REPLACE VIEW v_machine_daily_hours AS
WITH readings AS (
    SELECT
        e.ref_no,
        e.event_date,
        e.occurred_at,
        e.run_seconds,
        e.reported_branch_id,
        COALESCE(
            LAG(e.run_seconds) OVER w - e.run_seconds > 3600,
            FALSE
        ) AS is_reset
    FROM telemetry_events e
    WINDOW w AS (PARTITION BY e.ref_no, e.event_date ORDER BY e.occurred_at, e.run_seconds)
),
segmented AS (
    SELECT
        *,
        COUNT(*) FILTER (WHERE is_reset) OVER (
            PARTITION BY ref_no, event_date ORDER BY occurred_at, run_seconds
        ) AS segment
    FROM readings
),
segments AS (
    SELECT ref_no, event_date, segment, MAX(run_seconds) - MIN(run_seconds) AS seconds
    FROM segmented
    GROUP BY ref_no, event_date, segment
),
daily AS (
    SELECT
        ref_no,
        event_date,
        SUM(seconds)::BIGINT AS run_seconds,
        COUNT(*) - 1 AS reset_count
    FROM segments
    GROUP BY ref_no, event_date
),
daily_branch AS (
    SELECT
        ref_no,
        event_date,
        MODE() WITHIN GROUP (ORDER BY reported_branch_id) AS reported_branch_id
    FROM telemetry_events
    GROUP BY ref_no, event_date
)
SELECT
    d.event_date,
    d.ref_no,
    m.machine_type,
    assigned.name AS assigned_branch,
    reported.name AS reported_branch,
    d.run_seconds,
    ROUND(d.run_seconds / 3600.0, 2) AS run_hours,
    d.reset_count
FROM daily d
JOIN daily_branch db USING (ref_no, event_date)
JOIN machines m USING (ref_no)
JOIN branches assigned ON assigned.id = m.assigned_branch_id
JOIN branches reported ON reported.id = db.reported_branch_id;

-- Countable events per driver, machine and day. Routine updates are excluded, and
-- driver_name is NULL when nobody was logged on: those events are never guessed.
CREATE OR REPLACE VIEW v_driver_events AS
SELECT
    e.event_date,
    d.display_name AS driver_name,
    e.ref_no,
    m.machine_type,
    b.name AS reported_branch,
    e.event_type,
    t.category,
    COUNT(*)::INTEGER AS events
FROM telemetry_events e
JOIN event_types t ON t.name = e.event_type
JOIN machines m ON m.ref_no = e.ref_no
JOIN branches b ON b.id = e.reported_branch_id
LEFT JOIN drivers d ON d.id = e.driver_id
WHERE t.counts_as_event
GROUP BY e.event_date, d.display_name, e.ref_no, m.machine_type, b.name, e.event_type, t.category;

-- Activity per branch per day, using the branch each machine reported from.
CREATE OR REPLACE VIEW v_branch_daily AS
WITH hours AS (
    SELECT
        event_date,
        reported_branch AS branch,
        SUM(run_seconds) AS run_seconds,
        COUNT(*)::INTEGER AS active_machines
    FROM v_machine_daily_hours
    GROUP BY event_date, reported_branch
),
events AS (
    SELECT
        event_date,
        reported_branch AS branch,
        COALESCE(SUM(events) FILTER (WHERE event_type = 'Impact'), 0)::INTEGER AS impacts,
        COALESCE(
            SUM(events) FILTER (WHERE category = 'safety' AND event_type <> 'Impact'), 0
        )::INTEGER AS harsh_events,
        COALESCE(SUM(events) FILTER (WHERE category = 'idle'), 0)::INTEGER AS idle_events
    FROM v_driver_events
    GROUP BY event_date, reported_branch
)
SELECT
    h.event_date,
    h.branch,
    ROUND(h.run_seconds / 3600.0, 2) AS run_hours,
    h.active_machines,
    COALESCE(e.impacts, 0) AS impacts,
    COALESCE(e.harsh_events, 0) AS harsh_events,
    COALESCE(e.idle_events, 0) AS idle_events
FROM hours h
LEFT JOIN events e USING (event_date, branch);

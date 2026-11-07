# Pipeline

Loads each daily telemetry file into Postgres, cleaning it on the way. It runs every morning at 04:00 SAST through [GitHub Actions](../.github/workflows/ingest.yml).

| File | What it does |
| --- | --- |
| `clean.py` | The cleaning rules, as pure functions with no database or file access |
| `run.py` | Reads files oldest first, loads each in its own transaction, logs each attempt |
| `sql/001_schema.sql` | Tables, safe to run repeatedly. See the [data model](../docs/data_model.md) |
| `sql/002_views.sql` | The reporting views that the dashboard and chat read |

## Run it

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r pipeline/requirements-dev.txt
```

Set `DATABASE_URL`, then load. On Neon, use the direct connection string rather than the pooled one, because the pipeline's run lock needs a dedicated session.

```bash
.venv/Scripts/python pipeline/run.py
```

Add `--force` to reprocess files that are already loaded. On Linux or macOS, use `.venv/bin/python`.

## How a file is processed

```mermaid
flowchart TD
    A[File in data/incoming] --> B{Same content already loaded?}
    B -- Yes --> C[Skip, console log only]
    B -- No --> D[Clean rows]
    D -- File unusable --> E[Log failed, move to next file]
    D --> F[Transaction: replace this file's rows]
    F --> G[Insert events, ignoring known event keys]
    G --> H[Store rejected rows with reasons]
    H --> I[Log run: success or partial]
```

## Behaviour

**Safe to rerun.** Every event has a key hashed from its timestamp, machine, type, RunHours and driver. A file that's already loaded is skipped by checksum, and `--force` replaces that file's rows in one transaction, so the tables end up identical. Tests compare the tables before and after.

**One bad file can't stop the rest.** Each file has its own transaction. A failure rolls that file back, logs it, and moves on. The process then exits with code 1, so the scheduled run shows as failed. A failed file is retried on the next run.

**Row accounting.** Every raw row ends up loaded or in `rejected_rows`: `rows_total = rows_loaded + rows_rejected + rows_duplicate`.

| Rejection reason | Meaning |
| --- | --- |
| `duplicate_in_file` | The same event appears earlier in this file |
| `duplicate_across_files` | An earlier file already delivered this event |
| `unknown_machine` | The machine isn't on the machine list |
| `missing_machine` | The row has no machine reference |
| `unknown_branch` | The branch isn't one of the known branches |
| `unknown_event_type` | The event type isn't in the glossary |
| `invalid_timestamp` | The date isn't in a known format |
| `timestamp_out_of_range` | The date is on or after the delivery date, or over 7 days before it |
| `invalid_run_hours` | RunHours isn't a whole, non-negative number |
| `repeated_header` | A header row appears inside the data |
| `malformed_row` | The row has the wrong number of columns, which suggests a truncated file |

**Outcomes in `ingest_runs`.**

| Outcome | Meaning |
| --- | --- |
| `success` | The file loaded. Individual rows may still have been rejected |
| `partial` | The file loaded, but a malformed row suggests some data is missing |
| `failed` | Nothing from the file loaded, and `error` says why |

A file fails if its name doesn't match the expected pattern, it's empty or isn't valid UTF-8, a required column is missing, or no row is usable.

**Missing days.** A gap between delivery dates is logged as `deliveries_missing`. Sending an alert on this is part of the [production design](../docs/solution_design.png) rather than this build.

## Weekly report

`weekly_report.py` publishes a summary of the latest Monday-to-Sunday week. [GitHub Actions](../.github/workflows/weekly-report.yml) runs it every Monday at 07:00 SAST, three hours after the load that delivers Sunday's events. The app shows it at `/report`, where it can be saved as a PDF.

```bash
pip install -r app/api/requirements.txt
python pipeline/weekly_report.py
```

It needs `DATABASE_URL`, and `OPENROUTER_API_KEY` for the commentary. In GitHub Actions, both are repository secrets.

- **Figures come from code.** It reuses the dashboard's `build_dashboard`, so the report can't disagree with the dashboard.
- **The LLM only writes the commentary.** It's forced to submit through a typed tool. Every figure and machine reference must appear in the week's figures, or it gets up to 2 more attempts.
- **It fails safely.** If the model is down or its text never passes, the report still publishes with the figures, and the next run tries the commentary again.
- **Safe to rerun.** There's one row per week in `weekly_reports`. If the figures haven't changed, the run does nothing and costs nothing. `--force` writes the commentary again.
- **No data fails the run.** If there's nothing to report, it exits with code 1 so the run shows as failed.

## Test it

Unit tests need nothing else. Integration tests need a disposable Postgres, and they wipe the database named in `TEST_DATABASE_URL`.

```bash
docker run -d --name ridgeback-test-db -e POSTGRES_PASSWORD=testonly -e POSTGRES_DB=ridgeback_test -p 55432:5432 postgres:17-alpine
```

```bash
cd pipeline && TEST_DATABASE_URL=postgresql://postgres:testonly@localhost:55432/ridgeback_test ../.venv/Scripts/python -m pytest -q
```

## Troubleshoot

```sql
-- What happened recently?
SELECT file_name, outcome, rows_loaded, rows_rejected, rows_duplicate, error
FROM ingest_runs ORDER BY id DESC LIMIT 10;

-- Why were rows rejected?
SELECT source_file, reason, COUNT(*) FROM rejected_rows GROUP BY 1, 2 ORDER BY 1, 2;
```

If a new machine appears as `unknown_machine`, add it to `data/machine_list.csv` and run with `--force`. Its held rows then load.

## Security

`DATABASE_URL` comes from the environment: a GitHub Actions secret when scheduled, and an ignored `.env` locally. All SQL uses bound parameters, so file contents can't run as SQL.

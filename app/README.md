# App

One hosted application: a FastAPI service (`api/`) and a Next.js interface (`web/`). They deploy together as a single Vercel project using [`vercel.json`](../vercel.json), which sends `/api/v1/*` to FastAPI and everything else to Next.js.

Next.js only displays data. All database access, business logic and LLM calls are in FastAPI, and the dashboard and chat share [`queries.py`](api/queries.py), so their figures can't disagree.

## Headline

The sentence at the top of the dashboard comes from `build_headline()` in [`dashboard.py`](api/dashboard.py). It says only what the KPI tiles don't, such as the busiest branch or the day with the most impacts. It uses plain rules rather than the LLM, so it costs nothing, responds instantly and can't invent anything.

## Needs attention

The API builds this list, critical items first, and each item carries the question its **Ask** button sends to the chat. Items follow the filters. A cut-off file shows only for its own day. A machine that isn't on the list has no known type, so it's left out of machine type views, and its branch comes from its raw row.

## API contract

FastAPI publishes the full contract at `/api/v1/docs`. Models are in [`schemas.py`](api/schemas.py).

| Route | Purpose |
| --- | --- |
| `GET /api/v1/health` | Liveness check |
| `GET /api/v1/dashboard?day=&branch=&machine_type=` | All dashboard data for one view. With no `day`, returns the latest week. A date outside the data returns 422 |
| `POST /api/v1/chat` | Body: `{question, history}`. Streams newline-delimited JSON: `status` updates, then one `answer` or `error` |

## How the chat answers

```mermaid
sequenceDiagram
    participant U as Browser
    participant A as FastAPI agent
    participant M as OpenRouter
    participant D as Postgres
    U->>A: Question
    A->>M: Question, calendar, tool list
    M-->>A: Call get_run_hours(...)
    A->>A: Validate arguments
    A->>D: Parameterised, read-only query
    D-->>A: Rows
    A->>M: Tool result
    M-->>A: Draft answer
    A->>A: Is every figure in a tool result?
    A-->>U: Answer and how it was found
```

| Risk | How it's handled |
| --- | --- |
| Made-up figures | A guard compares each figure with tool results. It allows one retry, then withholds the answer |
| Unanswerable questions | The prompt lists what the data doesn't record, and tools report dates outside the data |
| Wrong machine | A partial reference such as `4813` is accepted only if it matches one machine. With several matches, the chat asks which one is meant |
| Wrong dates | The server gives the model the calendar for the latest week, and the answer states the dates used |
| SQL injection | The model picks from typed tools and never writes SQL. All values are bound parameters |
| Prompt injection | The database connection is read-only, so a manipulated model has nothing to damage. The prompt also treats data as data |
| Cost | `max_tokens`, 5 tool rounds, a 500-character question limit, per-IP rate limit, and the spend cap on the key |
| Model outage | An OpenRouter fallback list, a 30-second timeout and friendly error messages |

Each chat logs one JSON line with its outcome, model, tokens, tools and duration. Question text isn't logged.

## Run it locally

Put `DATABASE_URL` and `OPENROUTER_API_KEY` in a `.env` file at the repo root, then run the API from the root:

```bash
.venv/Scripts/python -m pip install -r app/api/requirements-dev.txt
```

```bash
.venv/Scripts/python -m uvicorn main:app --port 8010 --app-dir app/api --env-file .env
```

In another terminal, run the interface. `API_URL` tells it where the API is:

```bash
cd app/web && npm install && API_URL=http://localhost:8010 npm run dev
```

## Test it

Tests use a scripted model, so they cost nothing. They wipe the database named in `TEST_DATABASE_URL`.

```bash
cd app/api && TEST_DATABASE_URL=postgresql://postgres:testonly@localhost:55432/ridgeback_test ../../.venv/Scripts/python -m pytest -q
```

To compare real models, which costs a few cents, run `app/api/evaluate.py`. Its results go to [`docs/model_evaluation.md`](../docs/model_evaluation.md).

## Deploy

| Where | Setting |
| --- | --- |
| Vercel env vars | `OPENROUTER_API_KEY`, `DATABASE_URL` (Neon pooled string, read-only role). `APP_URL` is optional and identifies the app to OpenRouter |
| GitHub Actions secret | `DATABASE_URL` (Neon direct string, owner role) |

Keep the API's dependencies in `requirements.txt`, with no `pyproject.toml` in `app/api/`. With tool settings in that file, the deployed API crashed on startup. Moving them to `pytest.ini` and `ruff.toml` fixed it, though Vercel's docs don't say which file takes priority.

Create the read-only role with [`readonly_role.sql`](../pipeline/sql/roles/readonly_role.sql) after the first pipeline run.

## Known limits

- The rate limit is per server instance, so it slows abuse rather than guaranteeing a global limit. The key's spend cap is the hard backstop.
- There's no login, because the brief asks for a public URL.
- The guard checks figures, not meaning. A real figure attached to the wrong machine would pass it, which is why the evaluation checks answers against independent figures.

# Scheduled Runs & Slack Notifications

Recurring evaluation runs driven by cron expressions, with optional
Slack alerts that include trend deltas vs. the previous run.

---

## What it does

- Define a **Schedule** that pairs an `EvalConfig` with a `Dataset` and a
  cron expression (daily / weekly preset, or custom 5-field cron).
- An in-process scheduler fires each enabled schedule at its next due time
  and creates a fresh `EvalRun` — identical to triggering one through
  `POST /api/runs`.
- When a *scheduled* run completes, the app POSTs a Block Kit message to a
  Slack incoming webhook summarising the run and showing accuracy / score /
  latency deltas vs. the previous completed run for the same schedule.
- An optional `min_accuracy` per schedule flips the message header to an
  alert (🚨) when accuracy drops below the threshold. The notification
  still fires either way.

Manual runs (`POST /api/runs`) do **not** post to Slack in v1.

---

## Packages used

| Package | Why |
|---|---|
| [`apscheduler`](https://apscheduler.readthedocs.io/) (≥ 3.10) | `AsyncIOScheduler` driving cron triggers in the FastAPI event loop. |
| [`croniter`](https://github.com/kiorky/croniter) (≥ 2.0) | Validates user-supplied cron expressions before persisting them. |
| `httpx` | Async POST to the Slack incoming-webhook URL. |

All three are declared in [pyproject.toml](../../pyproject.toml).

---

## Configuration

Two environment variables (loaded by Pydantic Settings in
[src/config.py](../../src/config.py)):

| Variable | Default | Purpose |
|---|---|---|
| `SLACK_WEBHOOK_URL` | _empty_ | Default webhook used when a schedule does not override it. If unset and a schedule has no override, the notifier silently no-ops. |
| `APP_BASE_URL` | _empty_ | Used to build deep links (`{base}/runs/{id}`) in the Slack "Open run" button. If unset, the button is omitted. |

A schedule may also set its own `slack_webhook_url`, which takes priority
over the global default.

---

## Architecture

```
┌──────────────────┐     create / patch / toggle     ┌──────────────────┐
│  /api/schedules  │ ───────────────────────────────▶│ ScheduleRepo + DB│
└──────────────────┘                                  └──────────────────┘
         │ sync_schedule(schedule)
         ▼
┌──────────────────┐  fires at cron time   ┌─────────────────────────┐
│ SchedulerService │ ────────────────────▶ │ _trigger_run(schedule_id)│
│ (APScheduler)    │                       │ • create EvalRun         │
└──────────────────┘                       │ • mark_triggered         │
         ▲                                 │ • run_evaluation(run_id) │
         │ start() on lifespan             └─────────┬───────────────┘
         │                                           ▼
┌──────────────────┐                      ┌─────────────────────────┐
│ FastAPI lifespan │                      │ eval_runner             │
│ (src/app.py)     │                      │ • runs the eval         │
└──────────────────┘                      │ • _maybe_notify_slack() │
                                          └─────────┬───────────────┘
                                                    ▼
                                          ┌─────────────────────────┐
                                          │ slack_notifier          │
                                          │ • build_blocks(...)     │
                                          │ • httpx POST            │
                                          └─────────────────────────┘
```

### Components

- **[`src/services/scheduler.py`](../../src/services/scheduler.py)** —
  Process-wide singleton `SchedulerService` wrapping
  `AsyncIOScheduler(timezone="UTC")`. Started in the FastAPI `lifespan`
  context manager and re-hydrates jobs from the `schedules` table on
  startup. Exposes `sync_schedule()`, `remove_schedule()` and
  `get_next_run_at()`. The job callable `_trigger_run` opens its own DB
  session, creates the `EvalRun` row with `scheduled_by_id` set, calls
  `mark_triggered`, then dispatches `run_evaluation` via
  `asyncio.create_task`.

- **[`src/services/slack_notifier.py`](../../src/services/slack_notifier.py)** —
  Pure builders + an async `send()`. `build_blocks()` produces a Block Kit
  payload (header, context, fields, optional "Open run" action). Deltas
  are computed against the previous completed run for the same schedule;
  arrows render `▲`/`▼` and respect direction (latency lower is better).
  Failures are logged and never raised — a broken webhook must not fail
  the run.

- **[`src/services/eval_runner.py`](../../src/services/eval_runner.py)** —
  At the end of `run_evaluation()` calls `_maybe_notify_slack(session, run_id)`.
  The whole call is wrapped in `try/except` and only fires for runs whose
  `scheduled_by_id` is set.

- **[`src/routers/schedules.py`](../../src/routers/schedules.py)** — JSON
  CRUD plus `/toggle` and `/run-now`. Cron is validated via
  `is_valid_cron()` (croniter); invalid → HTTP 422. Referenced config /
  dataset existence is enforced; missing → HTTP 404. After every
  mutation the router calls `get_scheduler_service().sync_schedule()` so
  APScheduler stays in sync with the DB.

- **[`src/db/models.py`](../../src/db/models.py)** — adds the
  `Schedule` table and a nullable `EvalRun.scheduled_by_id` FK
  (`ON DELETE SET NULL`). Migration:
  [`alembic/versions/008_add_schedules.py`](../../alembic/versions/008_add_schedules.py).

---

## Frontend

| File | Role |
|---|---|
| [`frontend/src/types/schedule.ts`](../../frontend/src/types/schedule.ts) | TypeScript shapes mirroring the API. |
| [`frontend/src/api/schedules.ts`](../../frontend/src/api/schedules.ts) | Plain `fetch` API client. |
| [`frontend/src/lib/cron.ts`](../../frontend/src/lib/cron.ts) | `buildPresetCron()` (Daily/Weekly → cron) and `describeCron()` (cron → human-readable). |
| [`frontend/src/pages/schedules/ScheduleList.tsx`](../../frontend/src/pages/schedules/ScheduleList.tsx) | Table with last run, next run, enable/disable, run now, edit, delete. |
| [`frontend/src/pages/schedules/ScheduleForm.tsx`](../../frontend/src/pages/schedules/ScheduleForm.tsx) | Shared form with **Daily / Weekly / Advanced** tabs, hour/minute inputs, day-of-week multi-select, Slack URL override, `min_accuracy` percent input. |
| `ScheduleNew.tsx` / `ScheduleEdit.tsx` | Thin wrappers around the form. |

A `Clock` icon entry in
[`Sidebar.tsx`](../../frontend/src/components/Sidebar.tsx) links to
`/schedules`.

---

## API reference

All endpoints under `/api/schedules` return JSON.

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/schedules` | List all schedules with `next_run_at` and `last_run` summary. |
| `POST` | `/api/schedules` | Create. `cron_expression` validated; refs checked. |
| `GET` | `/api/schedules/{id}` | Fetch one. |
| `PATCH` | `/api/schedules/{id}` | Partial update. |
| `POST` | `/api/schedules/{id}/toggle` | Flip `enabled`. |
| `POST` | `/api/schedules/{id}/run-now` | Trigger an immediate run; cron timing is unchanged. |
| `DELETE` | `/api/schedules/{id}` | Remove the row and unregister the APScheduler job. Past runs stay (FK is `SET NULL`). |

### Schedule shape

```jsonc
{
  "id": "abc...",
  "name": "Nightly accuracy check",
  "eval_config_id": "cfg_...",
  "dataset_id": "ds_...",
  "cron_expression": "0 9 * * *",   // 5-field cron, UTC
  "enabled": true,
  "slack_webhook_url": null,        // null → use global SLACK_WEBHOOK_URL
  "min_accuracy": 0.85,             // optional, 0..1
  "next_run_at": "2026-04-21T09:00:00+00:00",
  "last_run": { "id": "run_...", "status": "completed", "accuracy": 0.92 }
}
```

---

## Operational notes

- **Time zone**: UTC only. Cron expressions are interpreted as UTC.
- **Concurrency**: `coalesce=True` and `misfire_grace_time=60` — if the
  app was down when a job was due, at most one run fires when it returns.
- **Persistence**: APScheduler uses an in-memory job store; jobs are
  rehydrated from the `schedules` table on every startup.
- **Failure isolation**: Slack failures, webhook 4xx/5xx, missing
  `APP_BASE_URL`, and even a missing `schedules` table on startup all
  log warnings and never crash the app.
- **Resetting the scheduler**: deleting or toggling a schedule via the
  API immediately removes / replaces the underlying APScheduler job; no
  restart required.

---

## Testing

[`tests/test_schedules.py`](../../tests/test_schedules.py) covers:

- `is_valid_cron()` accepts standard expressions and rejects garbage.
- `build_blocks()` snapshots: no previous run, below threshold, with
  deltas.
- Router flow: invalid cron → 422; create / list / patch / toggle / delete;
  `run-now` creates a new `EvalRun` for the schedule.

The scheduler itself is patched out in router tests so no APScheduler
jobs actually register during the suite.

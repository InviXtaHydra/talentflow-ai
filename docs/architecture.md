# Architecture

A modular monolith: one FastAPI application, one worker process, one PostgreSQL database, and a Next.js frontend.

```
Browser ──► Next.js (3300) ──/api/*──► FastAPI (8300) ──► PostgreSQL + pgvector
                                          │                  ▲
                                          └─ enqueue task ───┤ background_tasks
                                                             │
                                    Worker ──claim (SKIP LOCKED)┘──► Ollama / OpenAI-compatible API
```

## Frontend (`frontend/`)

- **Same origin.** The browser only talks to Next.js; `/api/*` is rewritten to the API. Session cookies are therefore
  first-party (`HttpOnly`, `SameSite=Lax`) and no CORS is needed in the browser.
- **App Router with Cache Components.** Pages are thin server components that render a client feature component inside
  `<Suspense>`. Authenticated pages are rendered by a client-side app shell after `/auth/me`; they set `instant = false`.
  `proxy.ts` redirects to the login page when there is no session cookie (an optimistic check; the API authorizes every call).
- `features/<area>/` holds pages and their components, `components/ui/` the design system, `lib/api.ts` the API client
  (CSRF header, typed errors), `lib/i18n/` the Dutch dictionary, `types/api.ts` the response types.
- Server state uses TanStack Query. Editable forms keep a local draft initialized from server data with `useDraft`.

## Backend (`backend/app/`)

| Package | Responsibility |
|---|---|
| `api/v1/` | Routes only: validation, auth dependencies, response models |
| `services/` | Business logic (auth, candidates, jobs, matching, CV processing, optimization, applications, privacy, …) |
| `repositories/` | Non-trivial queries (vacancy search) |
| `models/` | SQLAlchemy models and enums |
| `schemas/` | Pydantic request/response models and the structured profile/CV formats |
| `integrations/` | AI providers, private file storage, e-mail |
| `workers/` | The background worker |
| `core/` | Configuration, errors, logging, security helpers, rate limiting |

Errors have one shape: `{"error": {"code", "message", "details"}}`. Messages are user-facing Dutch text; codes are stable.

## Background tasks

Long-running work (CV extraction, analysis, optimization, embeddings) is stored in `background_tasks` and executed by
`python -m app.workers.runner`:

- tasks are claimed with `SELECT … FOR UPDATE SKIP LOCKED`, so more workers can be added safely;
- an **idempotency key** returns the running task instead of starting a second one (double clicks, refreshes);
- failures from the AI provider are retried with backoff (`max_attempts`); configuration errors fail immediately;
- every task has a timeout; a task whose heartbeat stops (crashed or restarted worker) is re-queued or failed;
- progress (percentage + message) is shown in the UI via `GET /api/v1/tasks/{id}`;
- a daily job applies the retention policy.

PostgreSQL was chosen over Redis for the queue: it is already required, it gives durable, transactional tasks, and the
expected volume (a few tasks per user action) is far below what it handles. Redis can be added later for rate limiting
and caching when the API runs as several processes.

## Data model (main tables)

`users`, `user_sessions`, `auth_tokens` · `candidate_profiles` (confirmed profile as validated JSON + embedding),
`candidate_preferences` · `companies`, `company_memberships` · `jobs` (generated `tsvector`, embedding, normalized
annual salary), `job_skills` · `cv_documents` (private file reference, extracted text, extracted data kept separate from
the profile), `cv_versions` (original / optimized / manual, generated vs. edited content, source snapshot, match before
and after), `cv_analyses` · `job_matches` (result + input hash for staleness) · `saved_jobs`, `job_views` ·
`applications`, `application_status_history` · `notifications`, `assistant_messages` · `ai_usage_records`, `audit_logs`,
`background_tasks`.

All timestamps are UTC (`timestamptz`); the UI formats them for `nl-BE`.

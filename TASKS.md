# TalentFlow AI: roadmap

Status legend: `[x]` done and verified · `[~]` partially done (see note) · `[ ]` open

## Phase 1: Inspect and initialize
- [x] Inspect environment (Docker, Node 24, Ollama with qwen3:8b + nomic-embed-text; host Python 3.14, so the backend runs in a Python 3.12 container)
- [x] Monorepo layout (`frontend/`, `backend/`, `docs/`)
- [x] Docker Compose: Postgres (pgvector), Mailpit, API, worker, frontend
- [x] `.env.example` with every setting documented
- [x] Health checks (`/api/v1/health`, `/api/v1/health/ready`)

## Phase 2: Database and authentication
- [x] SQLAlchemy models + Alembic migration
- [x] Sessions in the database, HttpOnly cookie, CSRF double-submit token
- [x] Argon2id password hashing
- [x] Register / login / logout / me / email verification / password reset / account deletion
- [x] Roles (candidate, employer, admin), never taken from the client
- [x] Rate limiting on auth endpoints
- [x] Seed data (clearly marked demo records) + `create-admin` command

## Phase 3: Frontend foundation
- [x] Design system (tokens, light/dark theme, UI components)
- [x] Auth pages, onboarding, candidate dashboard
- [x] Dutch UI with a translation dictionary

## Phase 4: Jobs and companies
- [x] Companies, memberships, employer authorization
- [x] Vacancy CRUD (draft / published / closed)
- [x] Search: full-text + filters + sorting + pagination
- [x] Saved jobs, related jobs

## Phase 5: CV processing
- [x] Private uploads with magic-byte validation and size limits
- [x] PDF/DOCX text extraction
- [x] Structured extraction (AI, or a labelled rule-based fallback)
- [x] Extraction review → confirmed profile
- [x] CV analysis

## Phase 6: Matching
- [x] AI provider abstraction (Ollama, OpenAI-compatible, demo, test fake)
- [x] Deterministic, explainable scoring engine with configurable weights
- [x] Embeddings (pgvector) when configured, lexical fallback otherwise
- [x] Persisted matches with staleness detection
- [x] Recommendations

## Phase 7: CV optimization
- [x] Optimization workflow as a background task with progress status
- [x] Strict schema validation + fact check against the source profile
- [x] Workspace: before/after, changes, warnings, questions, editor
- [x] Version history, restore original
- [x] PDF + DOCX export (3 templates)
- [x] Recalculated match with the same engine

## Phase 8: Applications and employer workflows
- [x] Applications with status history and constraints
- [x] Employer applicant view and status changes
- [x] In-app notifications

## Phase 9: Polish and hardening
- [x] Backend tests (pytest)
- [x] Frontend unit tests (Vitest)
- [x] End-to-end test of the main journey (Playwright)
- [x] Lint + type checks
- [x] Clean-database migration check
- [x] Documentation

## Verification (2026-10-13)
- Backend: 52 pytest tests pass; ruff and mypy clean; Alembic upgrade → downgrade → upgrade → check on a clean database.
- Frontend: 11 Vitest tests pass; `tsc` and ESLint clean; production build passes (33 routes).
- End-to-end (Playwright, against the Docker stack with local Ollama): main candidate journey incl. real AI extraction and
  optimization, PDF/DOCX download, persistence and account deletion; plus failure states. Both pass.
- `npm audit --omit=dev` and `pip-audit`: no known vulnerabilities.

## Known limitations / open
See "Limitations and open work" in README.md (OCR, per-process rate limiting, UI only in Dutch, no external job feed
connected, legal review of privacy notice and terms, production deployment).

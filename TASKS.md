# TalentFlow AI: roadmap

Status legend: `[x]` done and verified · `[~]` partially done (see note) · `[ ]` open

## Phase 1: Inspect and initialize
- [x] Inspect environment (Docker, Node 24, Ollama with qwen3:8b + nomic-embed-text; host Python 3.14, so the backend runs in a Python 3.12 container)
- [ ] Monorepo layout (`frontend/`, `backend/`, `docs/`)
- [ ] Docker Compose: Postgres (pgvector), Mailpit, API, worker, frontend
- [ ] `.env.example` with every setting documented
- [ ] Health checks (`/api/v1/health`, `/api/v1/health/ready`)

## Phase 2: Database and authentication
- [ ] SQLAlchemy models + Alembic migration
- [ ] Sessions in the database, HttpOnly cookie, CSRF double-submit token
- [ ] Argon2id password hashing
- [ ] Register / login / logout / me / email verification / password reset / account deletion
- [ ] Roles (candidate, employer, admin), never taken from the client
- [ ] Rate limiting on auth endpoints
- [ ] Seed data (clearly marked demo records) + `create-admin` command

## Phase 3: Frontend foundation
- [ ] Design system (tokens, light/dark theme, UI components)
- [ ] Auth pages, onboarding, candidate dashboard
- [ ] Dutch UI with a translation dictionary

## Phase 4: Jobs and companies
- [ ] Companies, memberships, employer authorization
- [ ] Vacancy CRUD (draft / published / closed)
- [ ] Search: full-text + filters + sorting + pagination
- [ ] Saved jobs, related jobs

## Phase 5: CV processing
- [ ] Private uploads with magic-byte validation and size limits
- [ ] PDF/DOCX text extraction
- [ ] Structured extraction (AI, or a labelled rule-based fallback)
- [ ] Extraction review → confirmed profile
- [ ] CV analysis

## Phase 6: Matching
- [ ] AI provider abstraction (Ollama, OpenAI-compatible, demo, test fake)
- [ ] Deterministic, explainable scoring engine with configurable weights
- [ ] Embeddings (pgvector) when configured, lexical fallback otherwise
- [ ] Persisted matches with staleness detection
- [ ] Recommendations

## Phase 7: CV optimization
- [ ] Optimization workflow as a background task with progress status
- [ ] Strict schema validation + fact check against the source profile
- [ ] Workspace: before/after, changes, warnings, questions, editor
- [ ] Version history, restore original
- [ ] PDF + DOCX export (3 templates)
- [ ] Recalculated match with the same engine

## Phase 8: Applications and employer workflows
- [ ] Applications with status history and constraints
- [ ] Employer applicant view and status changes
- [ ] In-app notifications

## Phase 9: Polish and hardening
- [ ] Backend tests (pytest)
- [ ] Frontend unit tests (Vitest)
- [ ] End-to-end test of the main journey (Playwright)
- [ ] Lint + type checks
- [ ] Clean-database migration check
- [ ] Documentation

## Known limitations / open
See "Limitations" in README.md.

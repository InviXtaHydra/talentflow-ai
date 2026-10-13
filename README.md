# TalentFlow AI

An AI-assisted recruitment platform for the Belgian job market (Dutch and French vacancies):

- **Candidates** upload a CV (PDF/DOCX) or build a profile by hand, review what was extracted, and get vacancies ranked by an
  **explainable match score** (skills, experience, role, education, preferences, plus hard requirements shown separately).
- For any vacancy they can click **"Optimaliseer mijn cv voor deze vacature"**: a background job tailors the CV with a language
  model, a **fact check** keeps only claims that trace back to the verified profile, the match is recalculated with the same
  engine, and the result can be edited and exported as **PDF or DOCX** (three templates). Every version is stored; the original never changes.
- **Employers** manage a company profile, publish vacancies, receive applications with the CV the candidate chose to share, and update statuses.
- **Administrators** see platform statistics, manage users and vacancies, AI usage and the audit log.

The UI is in Dutch (Flemish usage); code, API and documentation are in English.

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router, Cache Components), React 19, TypeScript (strict), Tailwind CSS 4, Radix UI, TanStack Query, React Hook Form + Zod, Recharts |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, psycopg 3 |
| Data | PostgreSQL 16 + pgvector, full-text search |
| Background work | Durable task queue in PostgreSQL + a worker process (retries, timeouts, crash recovery) |
| AI | Provider layer: **Ollama** (local, default: `qwen3:8b` + `nomic-embed-text`) or any **OpenAI-compatible** API |
| Documents | pypdf, python-docx (read and write), ReportLab (PDF) |
| Dev services | Docker Compose, Mailpit (catches all e-mail) |

See [docs/architecture.md](docs/architecture.md), [docs/api.md](docs/api.md), [docs/ai-matching.md](docs/ai-matching.md) and [docs/security.md](docs/security.md).

## Quick start (Docker)

Requirements: Docker Desktop, and [Ollama](https://ollama.com) on the host for AI features.

```bash
# 1. Local AI models (once)
ollama pull qwen3:8b
ollama pull nomic-embed-text

# 2. Configuration
cp .env.example .env
#    Set SECRET_KEY and POSTGRES_PASSWORD (also inside DATABASE_URL) to random values:
#    python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# 3. Start everything (migrations run automatically when the API starts)
docker compose up --build -d

# 4. Optional: demo companies, vacancies and accounts (all labelled "Demo")
docker compose exec api python -m app.cli seed-demo
#    prints the demo accounts and a generated password; or pass --password

# 5. Optional: an administrator
docker compose exec api python -m app.cli create-admin admin@example.com "Beheerder"
```

| URL | What |
|---|---|
| http://localhost:3300 | Web app |
| http://localhost:8300/docs | API documentation (Swagger, development only) |
| http://localhost:8325 | Mailpit: verification and password-reset e-mails |

Demo accounts after seeding: `demo.kandidaat@example.com` (candidate with a complete profile and CV) and
`demo.werkgever@example.com` (employer of the demo company "Brightcode Studio").

## Development without rebuilding

```bash
docker compose up -d db mailpit api worker      # backend in Docker
cd frontend && npm install
BACKEND_INTERNAL_URL=http://localhost:8300 npm run dev -- -p 3300
```

Backend code changes need `docker compose up -d --build api worker` (or run uvicorn locally with Python 3.12 and
`DATABASE_URL=postgresql+psycopg://talentflow:<password>@localhost:5436/talentflow`).

## Database

- Migrations: `docker compose exec api alembic upgrade head` (also run on API start-up).
- New migration after a model change: `docker compose run --rm --no-deps -v ./backend:/app api alembic revision --autogenerate -m "..."`.
- A clean database: `docker compose down -v` (deletes **all** local data, including uploaded files).

## Tests and checks

```bash
# Backend: 52 tests (pytest, separate test database, fake AI provider, no network)
docker compose run --rm --no-deps -v ./backend:/app api pytest
docker compose run --rm --no-deps -v ./backend:/app api sh -c "ruff check app tests && mypy app"

# Frontend: unit tests, types, lint, production build
cd frontend
npm test
npm run typecheck && npm run lint && npm run build

# End-to-end (needs the running stack incl. Ollama; ~3 minutes, uses the real local model)
npx playwright install chromium   # once
npm run test:e2e
```

The main end-to-end journey: register → upload a CV (`tests/e2e/fixtures/`) → review and confirm the extraction →
dashboard matches → open a vacancy and its match explanation → optimize the CV (real AI call) → edit → save →
download PDF and DOCX → reload (persisted) → CV library → delete the account through the privacy page.

## Configuration

Every setting is documented in [.env.example](.env.example). The important ones:

| Variable | Meaning |
|---|---|
| `AI_PROVIDER` | `ollama` (default, local), `openai` (any OpenAI-compatible API, needs `AI_API_KEY` and optionally `AI_BASE_URL`), `none` |
| `AI_MODEL`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL` | Model names. Empty `EMBEDDING_PROVIDER` = lexical matching only |
| `EMAIL_BACKEND` | `smtp` (Mailpit locally, your SMTP server in production) or `console` |
| `MATCH_WEIGHT_SKILLS` … `MATCH_WEIGHT_PREFERENCES` | Optional overrides of the match weights |
| `INACTIVE_ACCOUNT_RETENTION_DAYS`, `OPERATIONAL_LOG_RETENTION_DAYS` | Retention policy |

**Without AI** (`AI_PROVIDER=none`) the platform keeps working: authentication, profiles, search, matching (lexical),
applications and exports. CV extraction falls back to a clearly labelled basic (rule-based) extraction; CV optimization,
AI feedback and the assistant return a clear "not configured" message. Only the seeded demo records get a rule-based,
explicitly labelled *simulated* optimization.

**Using a hosted model** sends CV content to that provider: review its data-processing terms and update the privacy notice first.

## Branding

Product name: `APP_NAME` (backend) and `NEXT_PUBLIC_APP_NAME` (frontend build). Colours are CSS tokens at the top of
`frontend/app/globals.css`; the logo is `frontend/components/logo.tsx` and `frontend/app/icon.svg`.
UI text lives in `frontend/lib/i18n/nl.ts`; add a language by adding a dictionary with the same shape.

## Limitations and open work

- **AI quality depends on the model.** With the default local `qwen3:8b` extraction is good, but CV rewrites are modest
  (often a new summary and re-ordering, few rewritten bullets). A larger model gives better rewrites; the fact check stays the same.
- **The fact check is a safeguard, not a guarantee.** It catches invented numbers, unsupported skills and changed hard facts;
  it can't judge every nuance, which is why users always review before exporting.
- **No OCR**: scanned (image-only) PDFs are detected and the user is asked for a text PDF/DOCX or manual entry.
- **Rate limiting is per API process** (in memory). With several API instances, move it to Redis (`app/core/rate_limit.py`).
- **Currencies**: salaries are compared after normalizing to EUR per year; other currencies are stored but not compared.
- **UI language**: Dutch only for now (French/English dictionaries still to be written). CVs can be generated in NL, FR or EN.
- **Job ingestion**: an interface (`app/services/job_ingestion.py`) and an admin import endpoint exist; no external feed is
  connected, and nothing is scraped.
- **Notifications** are in-app; e-mail is only used for verification and password reset.
- **Legal**: the privacy notice and terms are technical drafts and need legal review before a public launch. Technical
  measures alone don't make the platform GDPR compliant.
- Production deployment (TLS, backups, monitoring, a managed SMTP provider, secrets management) is not set up here.

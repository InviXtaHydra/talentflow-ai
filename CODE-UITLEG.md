# TalentFlow AI: de code stap voor stap uitgelegd

Dit document legt uit **hoe de code werkt**: van het grote plaatje tot wat er precies gebeurt als iemand op een knop
klikt. Het is geschreven voor iemand die de code wil begrijpen, aanpassen of uitleggen (bijvoorbeeld in een sollicitatiegesprek).

> Hoe je de app installeert en gebruikt, staat in [HANDLEIDING.md](HANDLEIDING.md).
> Een korte technische samenvatting staat in [README.md](README.md), extra achtergrond in [docs/](docs/).

Bestanden noem ik telkens met hun pad, zodat je ze er meteen bij kan nemen.

---

## Inhoud

1. [Het grote plaatje](#1-het-grote-plaatje)
2. [De mappen en wat erin zit](#2-de-mappen-en-wat-erin-zit)
3. [Stap 1: de app start op](#3-stap-1-de-app-start-op)
4. [Stap 2: de reis van één verzoek (request)](#4-stap-2-de-reis-van-één-verzoek-request)
5. [Stap 3: de lagen in de backend](#5-stap-3-de-lagen-in-de-backend)
6. [Stap 4: de database](#6-stap-4-de-database)
7. [Stap 5: inloggen en beveiliging](#7-stap-5-inloggen-en-beveiliging)
8. [Stap 6: achtergrondtaken en de worker](#8-stap-6-achtergrondtaken-en-de-worker)
9. [Stap 7: een cv uploaden en laten herkennen](#9-stap-7-een-cv-uploaden-en-laten-herkennen)
10. [Stap 8: de AI-laag](#10-stap-8-de-ai-laag)
11. [Stap 9: de matchscore berekenen](#11-stap-9-de-matchscore-berekenen)
12. [Stap 10: een cv optimaliseren met feitencontrole](#12-stap-10-een-cv-optimaliseren-met-feitencontrole)
13. [Stap 11: vacatures (inclusief de LinkedIn-weergave)](#13-stap-11-vacatures-inclusief-de-linkedin-weergave)
14. [Stap 12: de frontend](#14-stap-12-de-frontend)
15. [Stap 13: tests](#15-stap-13-tests)
16. [Recept: zelf een functie toevoegen](#16-recept-zelf-een-functie-toevoegen)
17. [Belangrijke ontwerpkeuzes en waarom](#17-belangrijke-ontwerpkeuzes-en-waarom)

---

## 1. Het grote plaatje

TalentFlow AI bestaat uit **vijf onderdelen** die elk in een eigen Docker-container draaien:

```
                    ┌───────────────────────┐
  Browser  ───────► │ Frontend (Next.js)     │  poort 3300
                    │ toont de pagina's      │
                    └──────────┬────────────┘
                               │  /api/*  wordt doorgestuurd
                               ▼
                    ┌───────────────────────┐        ┌──────────────────────┐
                    │ API (FastAPI, Python) │ ─────► │ PostgreSQL + pgvector│  poort 5436
                    │ regels, rechten, data │ ◄───── │ alle gegevens + taken│
                    └──────────┬────────────┘        └──────────▲───────────┘
                               │ zet een taak klaar             │ haalt taken op
                               ▼                                │
                    ┌───────────────────────┐                   │
                    │ Worker (Python)        │ ──────────────────┘
                    │ voert lange taken uit  │ ──────► Ollama (AI op je Mac)
                    └───────────────────────┘

                    Mailpit (poort 8325): vangt alle e-mails op
```

In één zin per onderdeel:

| Onderdeel | Taak |
|---|---|
| **Frontend** | Toont de schermen en stuurt verzoeken naar de API. Bevat geen bedrijfsregels. |
| **API** | Het brein: controleert wie je bent, wat je mag en voert de logica uit. |
| **Database** | Bewaart alles: gebruikers, vacatures, cv's, matches en ook de wachtrij met taken. |
| **Worker** | Doet het trage werk (AI) op de achtergrond, zodat de website snel blijft. |
| **Mailpit** | Een nep-mailbox voor ontwikkeling. |

Dit heet een **modulaire monoliet**: één backend-programma, maar netjes opgedeeld in modules. Het is eenvoudiger dan
microservices en ruim voldoende voor deze schaal.

---

## 2. De mappen en wat erin zit

```
talentflow-ai/
├── docker-compose.yml        ← beschrijft de 5 containers en hoe ze samenhangen
├── .env.example              ← alle instellingen met uitleg
│
├── backend/app/
│   ├── main.py               ← startpunt van de API
│   ├── cli.py                ← commando's: seed-demo, create-admin
│   ├── api/
│   │   ├── deps.py           ← "wie is de gebruiker?", rollen, CSRF-controle
│   │   └── v1/               ← de routes (URL's), één bestand per domein
│   ├── services/             ← de bedrijfslogica (het echte werk)
│   │   ├── matching/         ← matchscore (engine.py = de formule)
│   │   ├── cv/               ← cv lezen, herkennen, optimaliseren, feitencontrole
│   │   └── documents/        ← PDF- en DOCX-export
│   ├── models/               ← databasetabellen (entities.py) en vaste keuzelijsten (enums.py)
│   ├── schemas/              ← vorm van de gegevens die de API ontvangt en teruggeeft
│   ├── repositories/         ← ingewikkelde zoekopdrachten (vacatures zoeken)
│   ├── integrations/         ← koppelingen naar buiten: AI, bestandsopslag, e-mail
│   ├── workers/runner.py     ← de achtergrondworker
│   ├── core/                 ← configuratie, fouten, beveiliging, rate limiting, logging
│   ├── db/                   ← databaseverbinding en basisklassen
│   ├── utils/                ← hulpfuncties (loon omrekenen, afstanden, vaardigheden …)
│   └── seed/                 ← demogegevens
├── backend/alembic/versions/ ← databasemigraties (de geschiedenis van de tabelstructuur)
├── backend/tests/            ← automatische tests
│
└── frontend/
    ├── next.config.ts        ← stuurt /api door naar de backend
    ├── proxy.ts              ← stuurt niet-ingelogde bezoekers naar /login
    ├── app/                  ← de routes (elke map = een URL)
    ├── features/             ← de echte pagina-inhoud per domein
    ├── components/ui/        ← herbruikbare bouwstenen (Button, Card, Badge …)
    ├── components/layout/    ← menu's en paginaskelet
    ├── hooks/                ← herbruikbare React-logica (useMe, useDraft …)
    ├── lib/api.ts            ← de enige plek die met de API praat
    ├── lib/i18n/nl.ts        ← alle Nederlandse teksten
    └── types/api.ts          ← TypeScript-types van alle API-antwoorden
```

**Vuistregel:** hoe dieper je in de backend gaat (`api` → `services` → `models`), hoe minder het met het web te maken
heeft en hoe meer met de eigenlijke regels.

---

## 3. Stap 1: de app start op

### 3.1 Docker Compose

`docker compose up` leest `docker-compose.yml` en start de containers in de juiste volgorde:

1. **db** (PostgreSQL met de pgvector-extensie) start eerst en meldt zich "healthy".
2. **api** wacht op de database en voert dan dit commando uit:
   ```sh
   alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   Eerst worden alle **migraties** uitgevoerd (de tabellen worden bijgewerkt), daarna start de webserver.
3. **worker** start pas als de API gezond is: `python -m app.workers.runner`.
4. **frontend** start ook pas als de API gezond is.

### 3.2 De API: `backend/app/main.py`

```python
app = FastAPI(
    title=f"{settings.app_name} API",
    docs_url=None if settings.is_production else "/docs",   # Swagger enkel in ontwikkeling
    ...
)
register_error_handlers(app)            # alle fouten krijgen dezelfde vorm
app.add_middleware(CORSMiddleware, ...) # welke websites mogen de API aanroepen
@app.middleware("http")                 # extra beveiligingsheaders op elk antwoord
async def security_headers(...): ...
app.include_router(api_router)          # alle routes onder /api/v1
```

### 3.3 De instellingen: `backend/app/core/config.py`

Alle waarden uit `.env` worden ingelezen in één `Settings`-object (met Pydantic). Overal in de code haal je ze op met
`get_settings()`. Een fout in `.env` (bv. een tekst waar een getal hoort) wordt bij het opstarten meteen gemeld.

---

## 4. Stap 2: de reis van één verzoek (request)

We volgen wat er gebeurt als een kandidaat een vacature opent op `http://localhost:3300/jobs/<id>`.

```
① Browser vraagt /jobs/<id>
② Next.js: proxy.ts controleert of de pagina beschermd is (deze niet)
③ Next.js toont de pagina; de component JobDetailPage start
④ JobDetailPage roept api.get("/jobs/<id>") aan
⑤ De browser stuurt GET /api/v1/jobs/<id> naar Next.js (zelfde adres!)
⑥ next.config.ts stuurt het door naar FastAPI: http://api:8000/api/v1/jobs/<id>
⑦ FastAPI: verify_csrf (GET → overslaan), get_optional_user (cookie → gebruiker)
⑧ Route get_job() in api/v1/jobs.py
⑨ Service job_service.get_visible_job() en job_service.detail()
⑩ SQLAlchemy haalt de vacature, het bedrijf, de vaardigheden en de match op uit PostgreSQL
⑪ Het antwoord wordt gevalideerd tegen JobDetailOut en als JSON teruggestuurd
⑫ TanStack Query bewaart het antwoord; React toont de pagina
```

**Stap ④ tot ⑥ in de code:**

`frontend/lib/api.ts` is de enige plek die met de server praat:

```ts
async function request<T>(method, path, body?) {
  const headers = { Accept: "application/json" };
  if (method !== "GET") headers["X-CSRF-Token"] = await ensureCsrf();  // beveiliging, zie stap 5
  const response = await fetch(`/api/v1${path}`, { method, headers, body, credentials: "same-origin" });
  if (!response.ok) throw new ApiError(response.status, data.error.code, data.error.message);
  return response.json();
}
```

`frontend/next.config.ts` stuurt alles onder `/api` door:

```ts
async rewrites() {
  return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
}
```

**Waarom zo?** De browser praat alleen met één adres (poort 3300). Daardoor zijn cookies "first-party", werkt
`HttpOnly` en is er geen CORS-gedoe in de browser.

**Stap ⑦ tot ⑨ in de code**, `backend/app/api/v1/jobs.py`:

```python
@router.get("/jobs/{job_id}", response_model=JobDetailOut)
def get_job(job_id: uuid.UUID, db: DbSession, user: OptionalUser) -> JobDetailOut:
    return job_service.detail(db, user, job_service.get_visible_job(db, user, job_id))
```

Let op hoe kort dit is. `DbSession` en `OptionalUser` zijn **dependencies**: FastAPI vult ze automatisch in voordat de
functie draait (zie `api/deps.py`). De route doet zelf niets inhoudelijks; alles gebeurt in de service.

**Fouten** krijgen altijd dezelfde vorm (`backend/app/core/errors.py`):

```json
{ "error": { "code": "not_found", "message": "Vacature niet gevonden.", "details": null } }
```

In een service schrijf je gewoon `raise NotFoundError("Vacature niet gevonden.")`. De foutafhandeling maakt er een
404-antwoord van. De frontend toont `message` aan de gebruiker en gebruikt `code` om te beslissen wat er moet gebeuren.

---

## 5. Stap 3: de lagen in de backend

Elke functie gaat door dezelfde lagen. Zo blijft alles voorspelbaar:

| Laag | Map | Verantwoordelijkheid | Voorbeeld |
|---|---|---|---|
| **Route** | `api/v1/` | URL, invoer valideren, wie mag dit? | `get_job()` |
| **Schema** | `schemas/` | Vorm van de invoer en uitvoer (Pydantic) | `JobIn`, `JobDetailOut` |
| **Service** | `services/` | Bedrijfsregels | `job_service.create_job()` |
| **Repository** | `repositories/` | Ingewikkelde zoekopdrachten | `jobs.search_ids()` |
| **Model** | `models/` | Databasetabellen (SQLAlchemy) | `class Job` |

**Voorbeeld: een vacature aanmaken**

1. Route `create_job` in `api/v1/jobs.py` vraagt een `EmployerUser`. Kandidaten krijgen dus automatisch een 403.
2. FastAPI valideert de body tegen `JobIn` (`schemas/jobs.py`): titel minstens 3 tekens, loon tussen 0 en 1.000.000,
   minimumloon niet hoger dan maximum, een periode verplicht als er een loon is …
3. `job_service.create_job()`:
   ```python
   company = require_member(db, user, company_id)   # ben je lid van dit bedrijf?
   if body.status == "published":
       _require_verified_to_publish(user)            # e-mail bevestigd?
   job = Job(**data, company_id=company.id, ...)
   _set_skills(job, body.skills)                     # vaardigheden normaliseren, dubbels eruit
   _refresh_derived(db, job)                         # loon omrekenen naar € per jaar, content-hash
   _schedule_embedding(db, job)                      # worker: embedding berekenen
   db.commit()
   ```
4. Het antwoord gaat door `job_service.detail()` en wordt een `JobDetailOut`.

**Pydantic** (de schema's) is de poortwachter: wat niet aan het schema voldoet, komt de service nooit binnen. De service
kan er dus van uitgaan dat de gegevens geldig zijn.

---

## 6. Stap 4: de database

### 6.1 Modellen: `backend/app/models/entities.py`

Elke tabel is een Python-klasse. Zo ziet een stuk van `Job` eruit:

```python
class Job(IdMixin, TimestampMixin, Base):
    __tablename__ = "jobs"

    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, fk("companies.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    benefits: Mapped[list[str]] = mapped_column(JSONB, default=list)
    salary_annual_min_eur: Mapped[int | None] = mapped_column(Integer, index=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768))
    search_vector = mapped_column(TSVECTOR, Computed("... to_tsvector(title) || to_tsvector(description) ..."))

    company: Mapped[Company] = relationship(back_populates="jobs")
    skills: Mapped[list["JobSkill"]] = relationship(...)
```

Wat valt op?

- **`IdMixin`** geeft elke tabel een UUID als id; **`TimestampMixin`** voegt `created_at` en `updated_at` toe (altijd UTC).
- **`JSONB`** bewaart lijsten (taken, voordelen, procedure) zonder aparte tabel.
- **`Vector(768)`** (pgvector) bewaart de embedding, voor inhoudelijke gelijkenis.
- **`search_vector`** wordt door PostgreSQL zelf berekend en geïndexeerd: snelle volledige-tekstzoekopdrachten.
- **`salary_annual_min_eur`** is een afgeleid veld: elk loon (per uur, maand of jaar) wordt omgerekend naar euro per jaar,
  zodat je eerlijk kan filteren en sorteren.

### 6.2 De belangrijkste tabellen

| Groep | Tabellen |
|---|---|
| Accounts | `users`, `user_sessions`, `auth_tokens` |
| Kandidaten | `candidate_profiles`, `candidate_preferences` |
| Bedrijven | `companies`, `company_memberships` |
| Vacatures | `jobs`, `job_skills`, `saved_jobs`, `job_views` |
| Cv's | `cv_documents` (het bestand), `cv_versions` (origineel, geoptimaliseerd, eigen versie), `cv_analyses` |
| Matching | `job_matches` (score + uitleg + hash van de invoer) |
| Sollicitaties | `applications`, `application_status_history` |
| Overig | `notifications`, `assistant_messages`, `ai_usage_records`, `audit_logs`, `background_tasks` |

### 6.3 Sessies: `backend/app/db/session.py`

```python
engine = create_engine(get_settings().database_url, pool_pre_ping=True, pool_size=10)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db          # de route gebruikt deze sessie
    finally:
        db.close()        # altijd netjes sluiten, ook bij een fout
```

Elke request krijgt zijn eigen databasesessie via de dependency `DbSession`.

### 6.4 Migraties: `backend/alembic/versions/`

Een migratie is een script dat de databasestructuur stap voor stap bijwerkt. Elke migratie verwijst naar de vorige
(`down_revision`), zo ontstaat een ketting:

```
90d738b8d474  initial schema
      ↓
b3e1f0a2c7d9  job details (voordelen, team, procedure, uren, contractduur, startdatum, plaatsen)
```

`alembic upgrade head` voert alle nog niet uitgevoerde migraties uit. Dat gebeurt automatisch bij het starten van de API.

---

## 7. Stap 5: inloggen en beveiliging

### 7.1 Inloggen

`POST /api/v1/auth/login` (`api/v1/auth.py`):

```python
rate_limiter.hit(f"login-ip:{ip}", limit=30, window_seconds=300)          # max. 30 pogingen per IP per 5 min
rate_limiter.hit(f"login-email:{email}", limit=8, window_seconds=300)     # max. 8 per e-mailadres
user = auth_service.authenticate(db, body.email, body.password)
token, csrf_token = auth_service.create_session(db, user, user_agent, ip)
_set_session_cookies(response, token, csrf_token)
```

1. **Wachtwoord controleren** met **Argon2id** (`core/security.py`). Bestaat het e-mailadres niet, dan wordt toch een
   controle uitgevoerd tegen een nep-hash. Zo kan een aanvaller aan de reactietijd niet zien of een account bestaat.
2. **Sessie aanmaken**: een willekeurige token gaat naar de browser in een `HttpOnly`-cookie (`tf_session`). In de
   database staat enkel de **hash** van die token. Een gelekte database bevat dus geen bruikbare sessies.
3. Een tweede cookie, `tf_csrf`, bevat de CSRF-token.

### 7.2 Bij elk verzoek: wie ben je?

`api/deps.py`:

```python
def _load_session(request, db):
    token = request.cookies.get("tf_session")
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    if session is None or session.expires_at <= now or not session.user.is_active:
        return None
    return session
```

Daarop bouwen kleine, herbruikbare "dependencies":

```python
OptionalUser  = ...  # gebruiker of None (publieke pagina's)
CurrentUser   = ...  # verplicht ingelogd, anders 401
CandidateUser = Annotated[User, Depends(require_roles(UserRole.CANDIDATE))]
EmployerUser  = Annotated[User, Depends(require_roles(UserRole.EMPLOYER, UserRole.ADMIN))]
AdminUser     = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
```

Een route die `user: AdminUser` vraagt, is daarmee automatisch afgeschermd. **De rol komt altijd uit de database, nooit
uit de browser.**

### 7.3 CSRF-bescherming

CSRF is een aanval waarbij een andere website jouw browser een verzoek laat sturen. In `api/v1/router.py` staat
`verify_csrf` als dependency op **alle** routes:

- GET-verzoeken worden overgeslagen (die mogen niets wijzigen).
- Bij andere verzoeken moet de header `X-CSRF-Token` gelijk zijn aan de cookie `tf_csrf` én aan de token van je sessie.
  Ook de `Origin`-header wordt gecontroleerd.

Een vreemde website kan jouw cookies niet lezen en dus de header niet meesturen. `lib/api.ts` doet dat automatisch
voor elke POST, PATCH, PUT en DELETE.

### 7.4 Rechten op gegevens

Rollen zijn niet genoeg: een werkgever mag alleen *zijn eigen* bedrijf beheren. Daarom controleert de service dat
ook nog eens:

```python
def require_member(db, user, company_id):           # services/company_service.py
    if user.role == UserRole.ADMIN: return company
    if membership(db, user, company_id) is None:
        raise PermissionDeniedError("Je hebt geen toegang tot dit bedrijf.")
```

Zo ook voor cv's (`get_document` controleert `user_id`) en taken (`tasks.get_for_user`).

### 7.5 Overige beveiliging

- **Uploads** (`services/cv/documents.py`): het bestandstype wordt bepaald aan de hand van de **echte inhoud** (magic
  bytes), niet de bestandsnaam, en extensie en inhoud moeten overeenkomen.
- **Bestandsopslag** (`integrations/storage/local.py`): bestanden krijgen een willekeurige naam
  (`secrets.token_hex(24)`), staan buiten de webmap en hebben bestandsrechten `0o600`.
- **Beveiligingsheaders** in `main.py` en `next.config.ts` (`nosniff`, `X-Frame-Options` …).
- **Auditlog** (`services/audit.py`) voor belangrijke acties.

---

## 8. Stap 6: achtergrondtaken en de worker

### 8.1 Het probleem

Een cv laten herkennen door de AI duurt 20 tot 120 seconden. Als de API daarop zou wachten, hangt de pagina en kan de
verbinding verbreken. Daarom: **de API zet een taak klaar, de worker voert ze uit, de browser vraagt de voortgang op.**

### 8.2 Een taak klaarzetten: `services/tasks.py`

```python
def enqueue(db, type_, *, user_id, payload, idempotency_key=None, max_attempts=2, timeout_seconds=600):
    if idempotency_key:
        existing = db.scalar(select(BackgroundTask).where(BackgroundTask.idempotency_key == idempotency_key))
        if existing is not None and existing.status in (QUEUED, RUNNING):
            return existing           # dubbelklik? dan krijg je dezelfde taak terug
    task = BackgroundTask(type=type_, payload=payload, ...)
    db.add(task)
```

De **idempotency key** (bv. `extract_cv:<cv-id>`) voorkomt dat een dubbelklik of een herladen pagina twee keer
hetzelfde werk start.

### 8.3 De worker: `workers/runner.py`

Een eindeloze lus:

```python
while not stopping:
    elke 30 s:  recover_stalled()        # vastgelopen taken herstellen
    elke dag:   apply_retention()        # oude gegevens opruimen
    if not run_once(): time.sleep(...)   # één taak uitvoeren, of even wachten
```

**Een taak oppakken** gebeurt met een speciale SQL-truc:

```python
select(BackgroundTask)
    .where(status == QUEUED, run_after <= now)
    .order_by(created_at)
    .limit(1)
    .with_for_update(skip_locked=True)     # ← SELECT … FOR UPDATE SKIP LOCKED
```

`SKIP LOCKED` betekent: "neem de eerste taak die nog niemand anders vastheeft". Je kan dus meerdere workers naast
elkaar draaien zonder dat ze dezelfde taak uitvoeren.

**Welke code bij welke taak hoort**, staat in één woordenboek:

```python
HANDLERS = {
    "extract_cv":    _extract_cv,      # cv herkennen
    "analyze_cv":    _analyze_cv,      # cv-feedback
    "optimize_cv":   _optimize_cv,     # cv afstemmen op een vacature
    "embed_profile": _embed_profile,   # embedding van een profiel
    "embed_job":     _embed_job,       # embedding van een vacature
}
```

**Betrouwbaarheid:**
- Mislukt een AI-aanroep, dan wordt het later opnieuw geprobeerd (tot `max_attempts`).
- Elke voortgangsmelding is ook een **heartbeat** (`heartbeat_at`). Blijft die langer uit dan de time-out van de taak
  (worker gecrasht), dan zet `recover_stalled()` de taak terug in de wachtrij of markeert ze als mislukt.
- Bij `docker compose stop` (SIGTERM) maakt de worker eerst de huidige taak af.

### 8.4 Voortgang tonen

Een handler krijgt een `progress`-functie mee, bv. `progress(40, "Gegevens herkennen met AI")`. De frontend vraagt
`GET /api/v1/tasks/<id>` op en toont het percentage en de boodschap.

**Waarom PostgreSQL en geen Redis/Celery?** PostgreSQL is er al, taken zijn dan transactioneel (een taak en de gegevens
waarop ze werkt, worden samen opgeslagen) en het volume is klein. Eén onderdeel minder om te beheren.

---

## 9. Stap 7: een cv uploaden en laten herkennen

### 9.1 Uploaden: `services/cv/documents.py` → `upload()`

```python
if len(data) > settings.max_upload_bytes: raise AppError(..., status_code=413)
mime = detect_cv_type(data)                         # echte inhoud: PDF of DOCX?
if mime is None or extension not in ("pdf", "docx"): raise AppError(..., status_code=415)
storage_key = get_storage().save(data)             # privé opslaan
document = CVDocument(..., extraction_status=PENDING)
tasks.enqueue(db, "extract_cv", payload={"cv_id": str(document.id)}, idempotency_key=f"extract_cv:{document.id}")
audit(db, "cv.upload", ...)
db.commit()
```

### 9.2 Herkennen (in de worker): `run_extraction()`

```
15%  Tekst uit het document halen        → services/cv/parsing.py (pypdf, python-docx)
     │  Bijna geen tekst? → status NEEDS_OCR ("gescande PDF") en stoppen
40%  Gegevens herkennen met AI            → _ai_extract() met een vast schema
     │  AI faalt of niet ingesteld? → services/cv/rule_based.py (eenvoudige herkenning)
100% Klaar                                → status COMPLETED
```

**Slim detail bij PDF's:** de tekst wordt rij per rij opnieuw opgebouwd op basis van de positie van elk stukje tekst.
Zo blijven bij een cv met twee kolommen de datums naast de juiste functietitel staan.

**Slim detail bij de AI:** het schema (`services/cv/llm_schema.py`) heeft enkel **verplichte** velden, die wel `null`
mogen zijn. Kleine lokale modellen geven anders het kortst mogelijke (bijna lege) antwoord.

### 9.3 Bevestigen: `confirm()`

De herkende gegevens staan apart in `cv_documents.extracted_data`. Pas als de kandidaat op "Bevestigen" klikt, worden ze
naar het profiel gekopieerd en wordt een "origineel" in `cv_versions` gemaakt. **De AI schrijft nooit rechtstreeks in je
profiel.**

---

## 10. Stap 8: de AI-laag

### 10.1 Eén interface, meerdere providers: `integrations/ai/`

```
base.py             ← de "contracten": LLMProvider en EmbeddingProvider (Protocol)
ollama_provider.py  ← lokale AI via Ollama
openai_provider.py  ← elke OpenAI-compatibele API
fake.py             ← nep-AI voor de tests (geen netwerk)
factory.py          ← kiest de juiste provider op basis van AI_PROVIDER in .env
prompts.py          ← alle systeemprompts
```

De rest van de code weet niet welke AI erachter zit. Overschakelen is één regel in `.env`.

### 10.2 Gestructureerde antwoorden: `ollama_provider.py`

De AI moet JSON teruggeven dat exact aan een Pydantic-schema voldoet:

```python
json_schema = schema.model_json_schema()
for _attempt in range(2):
    content, usage = self._call(messages, fmt=json_schema, temperature=temperature)   # Ollama dwingt het schema af
    try:
        return schema.model_validate_json(content), total                              # Pydantic controleert
    except (ValidationError, json.JSONDecodeError):
        messages += [ ...vorige antwoord..., "Your answer did not match the JSON schema. Return only valid JSON..." ]
raise AIOutputError(...)
```

Klopt het antwoord niet, dan krijgt het model één tweede kans met de foutmelding erbij.

### 10.3 Registreren: `services/ai_service.py`

Elke AI-aanroep gaat via `ai_service.generate()` of `ai_service.chat()`. Die meten de duur, het aantal tokens en of het
lukte, en bewaren dat in `ai_usage_records`. Dat zie je terug in het beheerscherm.

### 10.4 Bescherming tegen prompt injection

Cv-tekst en vacatures worden tussen tags gezet (`<document>`, `<vacancy>`, `<profile>`) en de systeemprompt zegt dat
instructies daarin genegeerd moeten worden. Belangrijker: ook als dat zou mislukken, kan het model niets kwaads doen. Het
heeft geen tools, het antwoord wordt gevalideerd en gecontroleerd, en het ziet nooit gegevens van andere gebruikers.

---

## 11. Stap 9: de matchscore berekenen

### 11.1 Drie bestanden, drie taken

| Bestand | Taak |
|---|---|
| `services/matching/facts.py` | Zet een profiel en een vacature om naar eenvoudige "feiten" (`CandidateFacts`, `JobFacts`) |
| `services/matching/engine.py` | **De formule.** Pure functies, geen database. Makkelijk te testen. |
| `services/matching/service.py` | Haalt gegevens op, gebruikt de engine en bewaart het resultaat |

Die scheiding is bewust: de engine weet niets van databases of het web. Je kan ze testen met gewone Python-objecten.

### 11.2 De formule: `compute_match()` in `engine.py`

```python
skills_component       = score_skills(...)          # 35%
experience_component   = score_experience(...)      # 25%
role_component         = score_role(...)            # 20%
qualifications_comp.   = score_qualifications(...)  # 10%
preferences_component  = score_preferences(...)     # 10%

applicable   = [c for c in components if c["applicable"]]      # wat kan beoordeeld worden?
total_weight = sum(c["weight"] for c in applicable)             # gewichten herverdelen

if len(applicable) < 2 or not (skills of role beoordeelbaar):
    score = None                       # "onvoldoende gegevens", geen gok
else:
    score = round(sum(c["score"] * c["weight"] for c in applicable) / total_weight)
    if eligibility == "not_met":
        score = min(score, 60)         # harde eis niet vervuld → maximaal 60
```

Het resultaat is niet alleen een getal: het bevat per onderdeel de score en uitleg, de vaardigheden die overeenkomen en
ontbreken, de relevante ervaring, de voorkeurscontroles en de sterkste factoren. Daarmee bouwt de frontend de
uitleg op (`features/jobs/match-breakdown.tsx`).

**Enkele details uit de onderdelen:**

- **Vaardigheden**: `utils/skills.py` normaliseert namen (`JS` → `javascript`, `.NET Core` → `dotnet`). Verplichte
  vaardigheden tellen dubbel. Een vaardigheid telt ook als ze in de beschrijving van een job in je werkervaring staat.
- **Ervaring**: wordt in **maanden** gerekend. Overlappende periodes worden samengevoegd (`_merged_months`), stages tellen
  niet mee en datums met enkel een jaartal worden voorzichtig geschat.
- **Functie**: met embeddings is het `0,6 × cosinusgelijkenis + 0,4 × titelgelijkenis`; zonder embeddings een vergelijking
  op woorden.
- **Voorkeuren**: afstand via een tabel met Belgische plaatsen en de haversine-formule (`utils/geo.py`), loon na omrekening
  naar euro per jaar (`utils/salary.py`).

### 11.3 Bewaren en hergebruiken: `get_or_compute()` in `service.py`

Een match opnieuw berekenen bij elke paginaweergave zou verspilling zijn. Daarom:

```python
digest = input_hash(profile, prefs, job)        # hash van ALLES wat de score beïnvloedt
match = existing.get(job.id)
if match is None or match.input_hash != digest: # nieuw, of er is iets veranderd?
    computed = compute_match(facts, job_facts(job), weights)
    match.score, match.result, match.input_hash = computed["score"], computed, digest
```

De hash omvat het profiel, de voorkeuren, de vacature, de embeddings, de gewichten, de versie van het algoritme en de
huidige maand (ervaring groeit met de tijd). Verandert er iets, dan klopt de hash niet meer en wordt opnieuw berekend.

---

## 12. Stap 10: een cv optimaliseren met feitencontrole

`services/cv/optimizer.py` → `run()`, uitgevoerd door de worker:

```
10%  Bronprofiel en vacature verzamelen
     source = je bevestigde profiel (of een gekozen cv-versie)
20%  Verschillen met de vacature analyseren
     gap = _gap(source, job)          ← zonder AI: welke vaardigheden heb je, wat ontbreekt?
     match_before = _match(...)       ← score van het huidige cv
35%  Cv herschrijven voor deze vacature
     output = ai_service.generate(..., schema=OptimizerOutput)
80%  Feiten controleren tegen je profiel
     tailored, review = assemble(source, output, job_skills)   ← services/cv/factcheck.py
     match_after = _match(...)        ← score van het nieuwe cv, met DEZELFDE engine
     ontbrekende verplichte vaardigheden → als "gap" aan de kandidaat voorgelegd
100% Klaar → nieuwe rij in cv_versions + melding naar de kandidaat
```

### De feitencontrole: `services/cv/factcheck.py` → `assemble()`

Dit is het hart van de betrouwbaarheid. Het model mag **ordenen en herformuleren**, maar niet **verzinnen**:

- Namen, werkgevers, functietitels, datums, diploma's, certificaten, talen en contactgegevens worden **uit de bron
  gekopieerd**, niet uit het AI-antwoord.
- Elke herschreven zin moet verwijzen naar een bron-item (`source_refs`). Ze blijft alleen staan als ze:
  - **geen nieuwe getallen** bevat (`unsupported_numbers`: getallen in de nieuwe tekst min getallen in de bron);
  - **geen nieuwe vaardigheden** noemt (`unsupported_skills`).
- Vaardigheden worden beperkt tot wat in het profiel staat.
- Alles wat afgekeurd wordt, wordt een **review item** dat de kandidaat te zien krijgt.
- De wijzigingsnotities worden opnieuw berekend uit de echte verschillen (`describe_changes`), niet blind overgenomen
  van het model.

Het resultaat bewaart zowel `generated_content` (wat de AI maakte, onveranderlijk) als `content` (wat de kandidaat
bewerkt). Zo kan je altijd terug.

### Exporteren: `services/documents/`

- `pdf.py` maakt de PDF met **ReportLab** (drie sjablonen: modern, minimaal, technisch).
- `docx_export.py` maakt een Word-bestand met **python-docx**.
- `labels.py` bevat de koppen in NL, FR en EN.

---

## 13. Stap 11: vacatures (inclusief de LinkedIn-weergave)

### 13.1 Zoeken: `repositories/jobs.py`

De zoekfunctie combineert:
- **volledige tekst** via de kolom `search_vector` (PostgreSQL `tsvector`, taalneutraal voor NL en FR);
- **filters**: plaats en afstand, thuiswerk, contracttype, niveau, sector, vaardigheden, minimumloon, taal;
- **sorteren** op relevantie, datum, loon of match. Bij "match" worden de scores eerst berekend en daarna gesorteerd
  (in `job_service.search`).

### 13.2 De detailpagina: `job_service.detail()`

Naast de basisgegevens verzamelt deze functie alles voor de LinkedIn-achtige weergave:

```python
open_jobs = count(Job where company == this company and status == PUBLISHED)
applicant_count = count(Application where job == this job
                        and status not in (SAVED, READY_TO_APPLY))   # enkel echte sollicitaties
view_count = count(JobView where job == this job)                   # 1 rij per kandidaat (unieke kijkers)
author = db.get(User, job.created_by_user_id)                       # het wervingsteam

return JobDetailOut(
    ...,
    benefits=job.benefits, about_team=job.about_team, hiring_process=job.hiring_process,
    department=..., hours_per_week=..., contract_duration_months=..., start_date=..., openings=...,
    company_profile=CompanyProfileOut(description, website_url, size, open_jobs),
    recruiter=RecruiterOut(full_name=author.full_name) if author and author.role != ADMIN else None,
    applicant_count=applicant_count, view_count=view_count,
)
```

Opent een kandidaat de pagina, dan wordt dat bijgehouden in `job_views` (`_record_view`): één rij per kandidaat per
vacature, met het tijdstip van de laatste weergave.

### 13.3 Demogegevens: `seed/`

- `demo_data.py` bevat fictieve bedrijven en 24 vacatures, plus per bedrijf en per taal de voordelen, de teamtekst
  en de procedure (`DEMO_COMPANY_DETAILS`), en per vacature de afdeling en de uren (`DEMO_JOB_EXTRAS`).
- `seed.py` maakt ze aan. Bestaat een demovacature al, maar mist ze de nieuwe velden, dan worden die één keer aangevuld.

---

## 14. Stap 12: de frontend

### 14.1 Routes: `frontend/app/`

Next.js gebruikt **mappen als URL's**. De mappen tussen haakjes zijn *groepen* met een eigen opmaak, maar komen niet in de URL:

| Groep | Voor wie | Voorbeelden |
|---|---|---|
| `(public)` | iedereen | `/`, `/login`, `/register`, `/privacy` |
| `(browse)` | iedereen, met of zonder login | `/jobs`, `/jobs/[id]`, `/companies` |
| `(app)` | enkel ingelogd | `/dashboard`, `/cv`, `/employer/jobs`, `/admin` |

Een `page.tsx` is bewust heel dun:

```tsx
// app/(browse)/jobs/[id]/page.tsx
export const metadata = { title: "Vacature" };
export default function Page() {
  return <PageSuspense><JobDetailPage /></PageSuspense>;
}
```

De echte inhoud staat in `features/jobs/job-detail.tsx`. Zo blijven routes en inhoud gescheiden.

### 14.2 Beschermde pagina's: `proxy.ts`

```ts
const PROTECTED = ["/dashboard", "/profile", "/cv", "/employer", "/admin", ...];
if (PROTECTED.some(...) && !request.cookies.has("tf_session")) {
  return NextResponse.redirect(new URL("/login?next=...", request.url));
}
```

Dit is enkel een **snelle, optimistische** controle voor een goede gebruikerservaring. De echte controle gebeurt altijd
in de API. Hetzelfde geldt voor `components/require-role.tsx`, dat de verkeerde rol een nette melding toont.

### 14.3 Gegevens ophalen: TanStack Query

```tsx
const job = useQuery({ queryKey: ["job", id], queryFn: () => api.get<JobDetail>(`/jobs/${id}`) });
if (job.error) return <QueryError error={job.error} />;
if (!job.data) return <PageSkeleton />;
```

- `queryKey` is het label in de cache. Na een wijziging zeg je `qc.invalidateQueries({ queryKey: ["job", id] })` en de
  gegevens worden opnieuw opgehaald.
- Instellingen in `components/providers.tsx`: 30 seconden "vers", geen herhaling bij 4xx-fouten en bij een 401 tijdens
  een wijziging (sessie verlopen) ga je naar de loginpagina.

**Wijzigen** gebeurt met `useMutation`, bijvoorbeeld de bewaarknop in `features/jobs/job-card.tsx`:

```tsx
const mutation = useMutation({
  mutationFn: () => (job.saved ? api.delete(`/jobs/${job.id}/save`) : api.post(`/jobs/${job.id}/save`)),
  onSuccess: () => {
    toast.success(job.saved ? "Niet meer bewaard" : "Vacature bewaard");
    qc.invalidateQueries({ queryKey: ["jobs"] });
    qc.invalidateQueries({ queryKey: ["job", job.id] });
  },
});
```

### 14.4 Formulieren: `hooks/use-draft.ts`

Een bewerkformulier (bv. `features/employer/job-form.tsx`) heeft een lokale kopie van de servergegevens nodig.
`useDraft` maakt die kopie en vernieuwt ze enkel als de `key` verandert (bv. `updated_at` van de vacature). Zo
overschrijft een achtergrondverversing niet wat je aan het typen bent.

Het formulier houdt alles als tekst bij (`FormState`) en zet het pas bij het opslaan om naar de API-vorm (`toBody`):
lege velden worden `null`, getallen worden `Number(...)` en lege regels in lijsten worden weggelaten.

### 14.5 Designsysteem: `components/ui/` en `app/globals.css`

- Kleuren zijn **CSS-variabelen** (`--accent`, `--surface`, `--text` …) met een lichte en een donkere versie. Tailwind
  gebruikt ze als `bg-surface`, `text-muted`, `bg-accent-soft` …
- Bouwstenen: `Button`, `Card`/`CardHeader`/`CardBody`, `Badge` en `Alert` (met tonen *neutral, accent, success,
  warning, danger*), `Dialog`, `Field`/`Input`/`Select`/`Textarea`, `TagInput`, `Tabs`.
- Iconen komen van `lucide-react`.

### 14.6 Teksten: `lib/i18n/nl.ts`

Herbruikbare teksten en keuzelijsten (bv. `enums.employmentType.full_time` → "Voltijds") staan in één woordenboek. In
de code: `t("enums.employmentType.full_time")`. Een nieuwe taal toevoegen = een woordenboek met dezelfde vorm toevoegen.

### 14.7 Types: `types/api.ts`

Voor elk API-antwoord bestaat een TypeScript-interface (`JobSummary`, `JobDetail`, `MatchResult` …). Voeg je in de
backend een veld toe aan een schema, voeg het hier dan ook toe. TypeScript wijst je dan elke plek aan die moet meeveranderen.

---

## 15. Stap 13: tests

### Backend: `backend/tests/` (pytest, 57 tests)

- `conftest.py` maakt een **aparte testdatabase** (`talentflow_test`, met dezelfde Alembic-migraties), maakt de tabellen leeg tussen tests en gebruikt de **nep-AI**
  (`integrations/ai/fake.py`). Er is geen netwerk nodig.
- De klasse `Api` in `conftest.py` doet wat de browser doet: een sessie bijhouden en de CSRF-header meesturen.
- Hulpfuncties: `register("employer")`, `verify(db, email)`, `create_job(api, **overrides)`, `fill_profile(api)`,
  `run_tasks()` (voert de wachtrij uit zoals de worker).

Een voorbeeld uit `tests/test_jobs.py`:

```python
def test_job_detail_shows_offer_team_process_and_activity(employer, candidate):
    job = create_job(employer, benefits=["Maaltijdcheques", "Opleidingsbudget"], hours_per_week=38, openings=2, ...)
    assert job["recruiter"]["full_name"] == employer.user["full_name"]

    candidate.post("/applications", {"job_id": job["id"], "channel": "external", "status": "saved"})
    assert candidate.get(f"/jobs/{job['id']}").json()["applicant_count"] == 0     # bewaren ≠ solliciteren
```

### Frontend

- **Vitest** (`npm test`, `frontend/tests/unit/`): de API-client, opmaakfuncties, de profieleditor en de matchuitleg.
- **Playwright** (`npm run test:e2e`): één volledige gebruikersreis in een echte browser, met de echte lokale AI.

### Codekwaliteit

- `ruff` (Python-stijl en veelgemaakte fouten), `mypy` (Python-types), `tsc --noEmit` (TypeScript), `eslint`.

---

## 16. Recept: zelf een functie toevoegen

Stel: je wil bij een vacature een veld **"reiskostenvergoeding ja/nee"** toevoegen.

| Stap | Bestand | Wat |
|---|---|---|
| 1 | `backend/app/models/entities.py` | `travel_allowance: Mapped[bool] = mapped_column(Boolean, default=False)` in `Job` |
| 2 | `backend/alembic/versions/…` | Migratie: `docker compose run --rm --no-deps -v ./backend:/app api alembic revision --autogenerate -m "travel allowance"` en het resultaat nakijken |
| 3 | `backend/app/schemas/jobs.py` | Veld in `_JobFields` (invoer), in `JobUpdate` (wijzigen) en in `JobDetailOut` (uitvoer) |
| 4 | `backend/app/services/job_service.py` | In `detail()`: `travel_allowance=job.travel_allowance` |
| 5 | `backend/tests/test_jobs.py` | Test: aanmaken met het veld en controleren dat het terugkomt |
| 6 | `frontend/types/api.ts` | `travel_allowance: boolean` in `JobDetail` |
| 7 | `frontend/features/employer/job-form.tsx` | In `FormState`, `empty`, `fromJob`, `toBody` en een `Checkbox` in het formulier |
| 8 | `frontend/features/jobs/job-detail.tsx` | Tonen, bv. als regel in `detailRows()` |
| 9 | Controleren | `pytest`, `npm run typecheck`, `npm run lint`, daarna `docker compose up -d --build` |

Moet het veld de **matchscore** beïnvloeden, dan komt het ook in `services/matching/facts.py` (in `JobFacts`), in
`engine.py` (in een `score_…`-functie) en in de `content_hash` in `_refresh_derived()`, zodat bestaande matches opnieuw
berekend worden.

Heeft de **AI-assistent** het nodig, voeg het dan toe aan de vacaturecontext in `services/assistant_service.py`.

---

## 17. Belangrijke ontwerpkeuzes en waarom

| Keuze | Waarom |
|---|---|
| **De score wordt berekend, niet door AI bedacht** | Uitlegbaar, reproduceerbaar, testbaar en eerlijk. Een taalmodel geeft bij dezelfde vraag niet altijd hetzelfde getal. |
| **Ontbrekende gegevens zijn geen mismatch** | Een leeg veld zegt niets over iemands geschiktheid. Gewichten herverdelen is eerlijker dan 0 punten. |
| **Feitencontrole na de AI** | Een cv met verzonnen ervaring kan iemand ernstig schaden. De AI krijgt ruimte om te formuleren, maar feiten komen uit de bron. |
| **Lokale AI (Ollama) als standaard** | Gratis en privé: cv's verlaten de computer niet. |
| **Wachtrij in PostgreSQL** | Geen extra dienst nodig, transactioneel en ruim voldoende voor dit volume. |
| **Same-origin via Next.js-rewrites** | HttpOnly-cookies werken, geen CORS in de browser, eenvoudiger beveiligd. |
| **Sessies in de database (geen JWT)** | Uitloggen en blokkeren werken meteen. Een JWT blijft geldig tot hij verloopt. |
| **Dunne routes, dikke services** | Bedrijfsregels staan op één plek en zijn bruikbaar vanuit routes, de worker en de seed. |
| **Engine zonder database** | De formule is te testen met eenvoudige objecten, zonder setup. |
| **Herkende cv-gegevens apart tot bevestiging** | De gebruiker houdt de controle. Fouten van de AI belanden niet ongemerkt in het profiel. |
| **Kandidaten niet rangschikken voor werkgevers** | Vermijdt automatische uitsluiting en past beter bij de AVG. |

---

*Tip: open naast dit document http://localhost:8300/docs. Daar zie je alle API-routes en kan je ze rechtstreeks uitproberen.*

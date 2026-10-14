# TalentFlow AI: volledige handleiding

Deze handleiding legt stap voor stap uit wat TalentFlow AI is, hoe je het installeert en opstart, en hoe je elk onderdeel
gebruikt als kandidaat, werkgever en beheerder. Achteraan staan de technische uitleg, de tests en een lijst met
veelvoorkomende problemen en oplossingen.

> Snel iets opzoeken? De korte technische samenvatting staat in [README.md](README.md). Diepere technische documentatie
> staat in de map [docs/](docs/).

---

## Inhoud

1. [Wat is TalentFlow AI?](#1-wat-is-talentflow-ai)
2. [Wat heb je nodig?](#2-wat-heb-je-nodig)
3. [Installatie in 5 stappen](#3-installatie-in-5-stappen)
4. [Eerste kennismaking met de demo](#4-eerste-kennismaking-met-de-demo)
5. [Tutorial: als kandidaat](#5-tutorial-als-kandidaat)
6. [Tutorial: als werkgever](#6-tutorial-als-werkgever)
7. [Tutorial: als beheerder](#7-tutorial-als-beheerder)
8. [Zo werkt de vacaturepagina](#8-zo-werkt-de-vacaturepagina)
9. [Zo werkt de matchscore](#9-zo-werkt-de-matchscore)
10. [Zo werkt de AI](#10-zo-werkt-de-ai)
11. [Instellingen (.env)](#11-instellingen-env)
12. [Dagelijks gebruik: starten, stoppen, updaten](#12-dagelijks-gebruik-starten-stoppen-updaten)
13. [Ontwikkelen aan de code](#13-ontwikkelen-aan-de-code)
14. [Testen](#14-testen)
15. [Problemen oplossen](#15-problemen-oplossen)
16. [Privacy en veiligheid](#16-privacy-en-veiligheid)
17. [Beperkingen en volgende stappen](#17-beperkingen-en-volgende-stappen)
18. [Woordenlijst](#18-woordenlijst)

---

## 1. Wat is TalentFlow AI?

TalentFlow AI is een rekruteringsplatform voor de Belgische arbeidsmarkt, met vacatures in het Nederlands, Frans en Engels.
Het brengt drie soorten gebruikers samen:

| Rol | Wat kan je doen? |
|---|---|
| **Kandidaat** | Cv uploaden, profiel nakijken, vacatures zoeken met een **uitlegbare matchscore**, je cv **per vacature laten optimaliseren door AI**, solliciteren en je sollicitaties opvolgen. |
| **Werkgever** | Bedrijfsprofiel beheren, uitgebreide vacatures publiceren (zoals op LinkedIn), sollicitaties ontvangen en de status ervan bijwerken. |
| **Beheerder** | Statistieken bekijken, gebruikers en vacatures beheren, AI-gebruik en het auditlogboek opvolgen. |

Wat het bijzonder maakt:

- **De matchscore wordt berekend, niet verzonnen.** Een vaste formule vergelijkt vaardigheden, ervaring, functie, opleiding
  en voorkeuren. Je ziet altijd *waarom* je een bepaalde score krijgt.
- **De AI draait lokaal** via [Ollama](https://ollama.com). Cv's verlaten je computer niet en het kost niets.
- **De AI mag niet liegen.** Een geoptimaliseerd cv wordt gecontroleerd tegen je echte profiel: verzonnen cijfers of
  vaardigheden worden eruit gehaald en aan jou voorgelegd.

---

## 2. Wat heb je nodig?

| Onderdeel | Waarom | Installeren |
|---|---|---|
| **Docker Desktop** | Draait de database, de API, de worker, de website en de testmailbox | [docker.com](https://www.docker.com/products/docker-desktop/) |
| **Ollama** | De lokale AI (cv's lezen, optimaliseren, assistent) | [ollama.com](https://ollama.com) |
| **Git** | Code ophalen | standaard aanwezig op macOS |
| *Node.js 24* (optioneel) | Alleen als je aan de frontend wil ontwikkelen of tests wil draaien | [nodejs.org](https://nodejs.org) |

Een computer met **minstens 16 GB RAM** is aangeraden. Het AI-model `qwen3:8b` gebruikt ongeveer 5 à 6 GB.

---

## 3. Installatie in 5 stappen

### Stap 1: de code ophalen

```bash
git clone https://github.com/InviXtaHydra/talentflow-ai.git
cd talentflow-ai
```

### Stap 2: de AI-modellen downloaden (eenmalig)

Zorg dat Ollama draait (je ziet het lama-icoontje in de menubalk). Daarna:

```bash
ollama pull qwen3:8b            # taalmodel: cv's lezen en herschrijven, assistent
ollama pull nomic-embed-text    # embeddings: inhoudelijke gelijkenis tussen profiel en vacature
```

### Stap 3: de configuratie aanmaken

```bash
cp .env.example .env
```

Open `.env` en vervang twee waarden door iets willekeurigs. Een sterke waarde maak je zo:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

- `SECRET_KEY=` → plak hier de gegenereerde waarde.
- `POSTGRES_PASSWORD=` → een tweede gegenereerde waarde. **Let op:** vervang hetzelfde wachtwoord ook in `DATABASE_URL`
  (het stuk tussen `talentflow:` en `@db`).

> `.env` bevat geheimen en staat in `.gitignore`. Zet dit bestand nooit op GitHub.

### Stap 4: alles opstarten

```bash
docker compose up --build -d
```

De eerste keer duurt dit enkele minuten. De database-migraties lopen automatisch bij het opstarten van de API.
Controleer of alles draait:

```bash
docker compose ps
```

Je zou vijf containers moeten zien: `db`, `mailpit`, `api` (healthy), `worker` en `frontend`.

### Stap 5: demogegevens en een beheerder (optioneel, maar aangeraden)

```bash
# Fictieve bedrijven, 24 vacatures en twee demo-accounts. Alles is gelabeld als "Demo".
docker compose exec api python -m app.cli seed-demo
# → toont de demo-accounts en een gegenereerd wachtwoord. Noteer dat wachtwoord!
#   Zelf een wachtwoord kiezen kan ook:  ... seed-demo --password "MijnWachtwoord123"

# Een beheerdersaccount
docker compose exec api python -m app.cli create-admin admin@example.com "Beheerder"
```

### Klaar! Open de app

| Adres | Wat |
|---|---|
| http://localhost:3300 | **De website** |
| http://localhost:8300/docs | API-documentatie (Swagger), enkel in ontwikkeling |
| http://localhost:8325 | **Mailpit**: hier komen alle e-mails binnen (verificatie, wachtwoord vergeten) |

---

## 4. Eerste kennismaking met de demo

Na `seed-demo` heb je twee accounts:

| Account | Rol | Wat zit erin? |
|---|---|---|
| `demo.kandidaat@example.com` | Kandidaat | Volledig profiel en een cv (Lotte Peeters, data/IT) |
| `demo.werkgever@example.com` | Werkgever | Eigenaar van het demobedrijf **Brightcode Studio** |

Het wachtwoord is het wachtwoord dat `seed-demo` toonde (of dat je zelf meegaf).

**Rondleiding in 5 minuten:**

1. Log in als **demo-kandidaat** → het dashboard toont je beste matches.
2. Klik op een vacature, bv. *Data Engineer* → bekijk de volledige vacature en rechts je **matchscore met uitleg**.
3. Klik op **"Optimaliseer mijn cv voor deze vacature"** → na 30 seconden tot 2 minuten krijg je een afgestemd cv.
4. Bekijk het verschil voor en na, pas aan waar nodig en download als **PDF** of **DOCX**.
5. Log uit, log in als **demo-werkgever** → bekijk *Vacatures* en *Kandidaten* van Brightcode Studio.

---

## 5. Tutorial: als kandidaat

### 5.1 Account aanmaken

1. Ga naar http://localhost:3300 en klik op **Gratis starten**.
2. Kies **Kandidaat**, vul naam, e-mail en wachtwoord in en aanvaard de voorwaarden.
3. Open **Mailpit** (http://localhost:8325) en klik op de verificatielink in de e-mail.

### 5.2 Onboarding: je cv uploaden

1. Na het inloggen start de **onboarding**. Upload je cv als **PDF of DOCX** (max. 5 MB).
2. De worker leest het cv en de AI haalt de gegevens eruit: contactgegevens, werkervaring, opleiding, vaardigheden,
   talen. Een voortgangsbalk toont waar hij zit.
3. Op **"Herkende gegevens nakijken"** controleer je alles. Pas aan wat niet klopt.
   - Stages worden apart herkend en tellen **niet** mee als werkervaring.
   - Een gescande PDF (een foto van tekst) kan niet gelezen worden. Je krijgt dan de vraag om een tekst-PDF of DOCX te
     uploaden of je profiel met de hand in te vullen.
4. Klik op **Bevestigen**. Pas dan komen de gegevens in je profiel. Niets wordt automatisch overgenomen zonder jouw akkoord.

> Liever geen cv uploaden? Via **Profiel** kan je alles ook met de hand invullen.

### 5.3 Je profiel en voorkeuren

Onder **Profiel** beheer je:

- je kopregel, samenvatting, woonplaats en telefoon;
- werkervaring, opleiding, vaardigheden, talen (met niveau), projecten en certificaten;
- **voorkeuren**: gewenste functies, plaatsen en maximale reisafstand, thuiswerk, contracttype, minimumloon en sectoren.

Hoe vollediger je profiel en voorkeuren, hoe betrouwbaarder je matchscore.

### 5.4 Vacatures zoeken

Onder **Vacatures**:

- zoek op trefwoord (titel en beschrijving);
- filter op plaats en afstand, thuiswerk, contracttype, niveau, sector, vaardigheden, minimumloon en taal;
- sorteer op **relevantie**, **datum**, **loon** of **beste match**.

Elke vacaturekaart toont je matchscore, de vaardigheden die je al hebt (groen) en wat er ontbreekt (oranje).
Met **Vacatures vergelijken** zet je twee tot vier vacatures naast elkaar.

### 5.5 Een vacature bekijken

Zie [hoofdstuk 8](#8-zo-werkt-de-vacaturepagina) voor alles wat op de vacaturepagina staat. Rechts zie je je
**matchscore** met per onderdeel uitleg.

### 5.6 Je cv optimaliseren voor een vacature

1. Klik op een vacature op **"Optimaliseer mijn cv voor deze vacature"**.
2. Kies waarvan je vertrekt (je bevestigde profiel of een eerdere cv-versie), de **taal** van het cv (NL, FR, EN) en een
   **sjabloon**:
   - *Modern professioneel*
   - *Minimaal (ATS-vriendelijk)*: het beste voor automatische selectiesystemen
   - *Technisch / developer*
3. Klik op **Start optimalisatie**. Dit duurt meestal 30 seconden tot 2 minuten.
4. Op het resultaatscherm zie je:
   - **voor en na** naast elkaar;
   - de **wijzigingen** die de AI maakte;
   - **waarschuwingen**: zinnen die de AI wou toevoegen maar die niet in je profiel staan, worden *niet* overgenomen maar
     aan jou voorgelegd;
   - **vragen** van de AI (bv. "heb je ervaring met X?");
   - de **matchscore voor en na**. Een hogere score betekent een betere presentatie, niet dat je plots meer kan.
5. Pas de tekst aan in de editor, sla op en download als **PDF** of **DOCX**.

Elke versie wordt bewaard onder **Mijn cv's**. Je origineel verandert nooit.

### 5.7 Solliciteren

Op de vacaturepagina heb je drie mogelijkheden:

| Knop | Wat gebeurt er? |
|---|---|
| **Solliciteren** | Via het platform. Je kiest welk cv je meestuurt, schrijft eventueel een motivatie en geeft toestemming om je gegevens met dat bedrijf te delen. |
| **Solliciteren op de website** | Opent de site van de werkgever. Daarna vraagt TalentFlow of je echt gesolliciteerd hebt. Enkel bij "ja" wordt het bijgehouden. |
| **Volgen in sollicitaties** | Zet de vacature in je overzicht zonder te solliciteren. |

### 5.8 Sollicitaties opvolgen

Onder **Sollicitaties** zie je al je sollicitaties met hun status:
*Bewaard → Klaar om te solliciteren → Gesolliciteerd → In behandeling → Gesprek → Aanbod* (of *Afgewezen* /
*Ingetrokken*). Elke statuswijziging wordt bijgehouden in een tijdlijn. Wijzigt een werkgever de status, dan krijg je een
**melding**.

### 5.9 Carrière-assistent

Onder **Carrière-assistent** stel je vragen over je profiel en tot drie vacatures, bijvoorbeeld:

- "Wat moet ik nog leren voor deze vacature?"
- "Schrijf een eerste versie van een motivatiebrief."
- "Wat bieden ze bij deze vacature, en hoe verloopt de sollicitatie?"

De assistent ziet alleen *jouw* profiel en de vacatures die je kiest. Hij verzint geen feiten en voert geen acties uit.

### 5.10 Cv-analyse

Onder **Mijn cv's → Cv-analyse** krijg je feedback op je cv: wat sterk is, wat ontbreekt en wat duidelijker kan.

### 5.11 Privacy en je gegevens

Onder **Privacy en gegevens** kan je:

- al je gegevens **downloaden** (export);
- je **account verwijderen**, inclusief je cv-bestanden.

---

## 6. Tutorial: als werkgever

### 6.1 Account en bedrijf

1. Klik op **Gratis starten** en kies **Werkgever**. Vul ook je bedrijfsnaam in.
2. Bevestig je e-mailadres via Mailpit. **Zonder bevestiging kan je enkel concepten opslaan, niet publiceren.**
3. Vul onder **Bedrijfsprofiel** je beschrijving, website, sector, plaats, grootte en logo in. Die gegevens verschijnen
   onderaan elke vacature in het blok *Over het bedrijf*.
4. Collega's toevoegen kan ook (rol *eigenaar* of *recruiter*).

### 6.2 Een vacature aanmaken

Ga naar **Vacatures → Nieuwe vacature**. Het formulier heeft vier blokken:

**1. Functie**
- Functietitel en beschrijving
- **Taken** (*Wat ga je doen?*): één taak per regel
- **Profiel / vereisten** (*Wie zoeken we?*)

**2. Aanbod, team en procedure**
- **Wat bieden jullie?** Voordelen zoals maaltijdcheques, hospitalisatieverzekering, opleidingsbudget of thuiswerk.
- **Over het team**: met wie werkt de kandidaat samen, en hoe?
- **Sollicitatieprocedure**: de stappen in volgorde, bv. *kennismakingsgesprek → technische opdracht → voorstel*.

**3. Vaardigheden en vereisten**
- Vaardigheden, telkens met het vinkje **Verplicht** of niet (een pluspunt). Verplichte vaardigheden wegen dubbel in de match.
- Minimum jaren ervaring, niveau (junior, medior, senior, lead) en vereiste opleiding
- Vereiste talen (taalcodes: `nl`, `fr`, `en` …)

**4. Voorwaarden**
- Plaats, thuiswerk (op locatie / hybride / volledig remote) en contracttype
- Loon van/tot (bruto) en per maand, jaar of uur
- Sector, **afdeling**, **uren per week**, **contractduur** (leeg = onbepaalde duur), **startdatum** (leeg = in overleg),
  **aantal plaatsen**
- Taal van de vacature, sollicitatiedeadline en eventueel een externe sollicitatielink

Onderaan kies je **Opslaan als concept** (alleen zichtbaar voor je bedrijf) of **Publiceren**. Een gepubliceerde
vacature kan je later **sluiten**: ze blijft dan leesbaar, maar solliciteren kan niet meer.

> **Tip:** vacatures met een concreet loon, duidelijke voordelen en een beschreven procedure krijgen meer en betere
> sollicitaties. Vul daarom zoveel mogelijk velden in.

### 6.3 Kandidaten beheren

Onder **Kandidaten** zie je alle sollicitaties op je vacatures:

- naam, e-mail en het cv dat de kandidaat koos om te delen (alleen met diens toestemming);
- de motivatie;
- de vaardigheden die overeenkomen met de vacature. Kandidaten worden bewust **niet gerangschikt**, om
  automatische uitsluiting te vermijden.

Wijzig de status (*In behandeling*, *Gesprek*, *Aanbod*, *Afgewezen*). De kandidaat krijgt daarvan een melding.

### 6.4 Overzicht

Het werkgeversdashboard (**Overzicht**) toont je open vacatures, nieuwe sollicitaties en recente activiteit.

---

## 7. Tutorial: als beheerder

Log in met het account dat je aanmaakte met `create-admin`. Onder **Beheer** vind je:

- **Statistieken**: gebruikers, vacatures, sollicitaties en optimalisaties;
- **Gebruikers**: bekijken, **blokkeren** (alle sessies worden meteen afgesloten) en weer activeren;
- **Vacatures**: alle vacatures van alle bedrijven bekijken en sluiten;
- **AI-gebruik**: per soort AI-taak hoeveel keer ze liep, hoeveel er lukten en hoe lang ze gemiddeld duurden;
- **Auditlogboek**: belangrijke acties (statuswijzigingen, blokkeringen, verwijderingen …).

Vacatures uit een geautoriseerde feed (bv. een partner-ATS) importeer je via de API: `POST /api/v1/admin/job-feeds/import`
(zie http://localhost:8300/docs). Er wordt nooit iets gescraped.

---

## 8. Zo werkt de vacaturepagina

De vacaturepagina is opgebouwd zoals op LinkedIn: alles wat een kandidaat wil weten, staat op één pagina.

**Bovenaan (kop)**
- Bedrijfslogo en naam, functietitel
- Plaats, **"Geplaatst 3 dagen geleden"**, **aantal sollicitanten** (of "Wees een van de eerste sollicitanten") en
  **aantal keer bekeken**
- Labels: thuiswerk, contracttype, niveau en loon
- Kernpunten: uren per week en contractduur, bedrijfsgrootte en sector, talen, vaardigheden (voor kandidaten: *"3 van 6 in
  je profiel"*), aantal open plaatsen en deadline
- Knoppen: Solliciteren, Bewaren, cv optimaliseren, volgen, assistent

**Over de vacature**
- Beschrijving
- *Wat ga je doen?* (taken)
- *Wie zoeken we?* (vereisten)
- *Vaardigheden*, opgesplitst in **Vereist** en **Pluspunten**. Vaardigheden die al in je profiel staan, kleuren groen.
- *Wat bieden we?*: loon en voordelen met vinkjes
- *Over het team*
- *Sollicitatieprocedure* als genummerde stappen

**Vacaturedetails**: een overzicht van senioriteit, dienstverband, werkplek, afdeling, sector, uren per week,
contractduur, startdatum, aantal vacatures, ervaring, opleiding, talen, taal van de vacature, deadline en
publicatiedatum. Velden die de werkgever niet invulde, worden weggelaten in plaats van "onbekend" te tonen.

**Over het bedrijf**: logo, sector, grootte, plaats, aantal open vacatures, beschrijving en links naar de bedrijfspagina
en de website.

**Zijkolom**: je matchscore met uitleg, het wervingsteam (wie de vacature plaatste) en een korte samenvatting.

**Onderaan**: gelijkaardige vacatures (op basis van gedeelde vaardigheden en sector).

> Het aantal sollicitanten telt alleen **echte** sollicitaties. Een vacature die iemand enkel bewaard heeft, telt niet mee.
> "Bekeken" telt het aantal kandidaten dat de vacature opende.

---

## 9. Zo werkt de matchscore

De matchscore (0–100) wordt **berekend met een vaste formule**. Een taalmodel geeft nooit zelf een percentage.

| Onderdeel | Gewicht | Wat wordt vergeleken? |
|---|---|---|
| **Vaardigheden** | 35% | Verplichte vaardigheden tellen dubbel. Synoniemen worden herkend (`JS` = `JavaScript`). Een vaardigheid telt ook als ze in je werkervaring vermeld staat. |
| **Ervaring** | 25% | Relevante werkervaring in **maanden** (stages tellen niet). Overlappende periodes tellen één keer. |
| **Functie** | 20% | Hoe goed je profiel en de vacature inhoudelijk op elkaar lijken (embeddings) plus de gelijkenis van functietitels. |
| **Opleiding** | 10% | Jouw hoogste diploma tegenover het gevraagde niveau. |
| **Voorkeuren** | 10% | Afstand, thuiswerk, contracttype, loon en sector tegenover jouw voorkeuren. |

**Belangrijke regels:**

- **Ontbrekende gegevens zijn geen mismatch.** Kan een onderdeel niet beoordeeld worden, dan valt het weg en worden de
  andere gewichten herverdeeld. De pagina zegt wat er ontbreekt.
- **Harde eisen** (vereiste talen, opleiding, minder dan de helft van de gevraagde ervaring, meer dan de helft van de
  verplichte vaardigheden ontbreekt) worden apart getoond. Is er één niet vervuld, dan is de score **maximaal 60**.
- Te weinig gegevens? Dan krijg je **geen score** ("onvoldoende gegevens") in plaats van een gok.
- Leeftijd, geslacht, afkomst, religie, handicap en foto's worden **nooit** gebruikt.

De gewichten zijn aanpasbaar in `.env` (`MATCH_WEIGHT_SKILLS`, `MATCH_WEIGHT_EXPERIENCE` …). Meer details staan in
[docs/ai-matching.md](docs/ai-matching.md).

---

## 10. Zo werkt de AI

| Taak | Model | Waar? |
|---|---|---|
| Cv lezen (gegevens herkennen) | `qwen3:8b` | Worker, op de achtergrond |
| Cv-analyse | `qwen3:8b` | Worker |
| Cv optimaliseren | `qwen3:8b` + **feitencontrole** | Worker |
| Carrière-assistent | `qwen3:8b` | API |
| Inhoudelijke gelijkenis (matching) | `nomic-embed-text` | Worker, bij elke wijziging van profiel of vacature |

**De feitencontrole bij het optimaliseren**
- Namen, werkgevers, functietitels, data, diploma's, talen en contactgegevens worden altijd **letterlijk overgenomen** uit
  je profiel.
- Een herschreven zin blijft alleen staan als ze **geen nieuwe cijfers** en **geen nieuwe vaardigheden** bevat.
- Wat afgekeurd wordt, krijg je te zien als *waarschuwing* of *vraag*.

**Achtergrondtaken**: lange taken lopen via een wachtrij in de database. Dubbelklikken start geen tweede taak, mislukte
AI-aanroepen worden opnieuw geprobeerd en een vastgelopen taak wordt automatisch hersteld.

**Zonder AI** (`AI_PROVIDER=none`) blijft alles werken behalve de AI-functies: cv-herkenning valt terug op een eenvoudige,
duidelijk gelabelde herkenning, en optimaliseren en de assistent tonen een duidelijke melding.

**Een ander model gebruiken**: zet `AI_PROVIDER=openai` met `AI_API_KEY` (en eventueel `AI_BASE_URL`) voor elke
OpenAI-compatibele dienst. Let op: dan verlaten cv-gegevens je computer. Pas eerst de privacyverklaring aan.

---

## 11. Instellingen (.env)

Alle instellingen staan met uitleg in [.env.example](.env.example). De belangrijkste:

| Variabele | Betekenis | Standaard |
|---|---|---|
| `SECRET_KEY` | Geheime sleutel voor sessies. **Altijd zelf invullen.** | — |
| `POSTGRES_PASSWORD` / `DATABASE_URL` | Databasewachtwoord (op beide plaatsen hetzelfde) | — |
| `AI_PROVIDER` | `ollama`, `openai` of `none` | `ollama` |
| `AI_MODEL` | Naam van het taalmodel | `qwen3:8b` |
| `AI_BASE_URL` | Waar Ollama draait, gezien vanuit Docker | `http://host.docker.internal:11434` |
| `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL` | Embeddings. Leeg = enkel woordvergelijking | `ollama` / `nomic-embed-text` |
| `EMAIL_BACKEND` | `smtp` (Mailpit lokaal) of `console` | `smtp` |
| `MAX_UPLOAD_MB` | Maximale cv-grootte | `5` |
| `MATCH_WEIGHT_*` | Gewichten van de matchscore | zie hoofdstuk 9 |
| `INACTIVE_ACCOUNT_RETENTION_DAYS` | Inactieve accounts verwijderen na X dagen (0 = nooit) | `0` |

Na een wijziging in `.env`: `docker compose up -d` (de containers worden dan opnieuw gestart met de nieuwe waarden).

---

## 12. Dagelijks gebruik: starten, stoppen, updaten

```bash
docker compose up -d                 # starten
docker compose stop                  # stoppen (gegevens blijven bewaard)
docker compose ps                    # wat draait er?
docker compose logs -f api worker    # live logboek van API en worker (Ctrl+C om te stoppen)

git pull                             # nieuwste code ophalen
docker compose up -d --build         # opnieuw bouwen en starten (migraties lopen automatisch)
docker compose exec api python -m app.cli seed-demo   # demovacatures aanvullen met nieuwe velden
```

**Alles wissen en opnieuw beginnen** (verwijdert *alle* lokale gegevens, ook geüploade cv's):

```bash
docker compose down -v
docker compose up --build -d
```

---

## 13. Ontwikkelen aan de code

### Mappenstructuur

```
talentflow-ai/
├── backend/                 Python 3.12, FastAPI
│   ├── app/
│   │   ├── api/v1/          routes (alleen validatie en rechten)
│   │   ├── services/        bedrijfslogica (jobs, matching, cv, sollicitaties …)
│   │   ├── models/          databasetabellen (SQLAlchemy)
│   │   ├── schemas/         in- en uitvoer van de API (Pydantic)
│   │   ├── integrations/    AI-providers, bestandsopslag, e-mail
│   │   ├── workers/         achtergrondworker
│   │   └── seed/            demogegevens
│   ├── alembic/versions/    databasemigraties
│   └── tests/               pytest
├── frontend/                Next.js 16, React 19, TypeScript, Tailwind CSS 4
│   ├── app/                 pagina's (routes)
│   ├── features/            pagina-onderdelen per domein (jobs, cv, employer …)
│   ├── components/ui/       designsysteem (knoppen, kaarten, formulieren)
│   ├── lib/i18n/nl.ts       alle Nederlandse teksten
│   └── types/api.ts         types van de API-antwoorden
├── docs/                    technische documentatie
├── docker-compose.yml
├── .env.example
├── README.md
└── HANDLEIDING.md           dit document
```

### Frontend zonder telkens te herbouwen

```bash
docker compose up -d db mailpit api worker
cd frontend && npm install
BACKEND_INTERNAL_URL=http://localhost:8300 npm run dev -- -p 3300
```

Wijzigingen in de frontend zijn dan meteen zichtbaar. Na wijzigingen in de backend:
`docker compose up -d --build api worker`.

### Voorbeeld: een veld aan een vacature toevoegen

Zo werden bijvoorbeeld *voordelen* en *sollicitatieprocedure* toegevoegd:

1. **Model**: kolom toevoegen in `backend/app/models/entities.py` (klasse `Job`).
2. **Migratie**: een bestand in `backend/alembic/versions/`, of automatisch:
   `docker compose run --rm --no-deps -v ./backend:/app api alembic revision --autogenerate -m "omschrijving"`.
3. **Schema**: veld toevoegen in `backend/app/schemas/jobs.py` (`_JobFields`, `JobUpdate`, `JobDetailOut`).
4. **Service**: invullen in `detail()` in `backend/app/services/job_service.py`.
5. **Types**: `frontend/types/api.ts`.
6. **Formulier**: `frontend/features/employer/job-form.tsx`.
7. **Weergave**: `frontend/features/jobs/job-detail.tsx`.
8. **Test**: `backend/tests/test_jobs.py`.

### Beheercommando's

```bash
docker compose exec api python -m app.cli seed-demo [--password ...]
docker compose exec api python -m app.cli create-admin <e-mail> "<naam>"
docker compose exec api alembic upgrade head      # migraties handmatig uitvoeren
docker compose exec api alembic current           # huidige databaseversie
```

---

## 14. Testen

```bash
# Backend: 57 tests (aparte testdatabase, nep-AI, geen internet nodig)
docker compose run --rm --no-deps -v ./backend:/app api pytest

# Codekwaliteit backend
docker compose run --rm --no-deps -v ./backend:/app api sh -c "ruff check app tests && mypy app"

# Frontend: unit tests, types, lint en productiebuild
cd frontend
npm test
npm run typecheck && npm run lint && npm run build

# End-to-end met een echte browser en de echte lokale AI (~3 minuten, de volledige stack moet draaien)
npx playwright install chromium   # eenmalig
npm run test:e2e
```

De end-to-end-test doorloopt de volledige kandidatenreis: registreren → cv uploaden → herkenning bevestigen → matches op
het dashboard → vacature en matchuitleg openen → cv optimaliseren met echte AI → aanpassen en opslaan → PDF en DOCX
downloaden → herladen → cv-bibliotheek → account verwijderen.

---

## 15. Problemen oplossen

| Probleem | Oorzaak | Oplossing |
|---|---|---|
| Website laadt niet op :3300 | Container draait niet | `docker compose ps` en `docker compose logs frontend` |
| `api` blijft *unhealthy* | Databasewachtwoord in `.env` klopt niet | `POSTGRES_PASSWORD` en het wachtwoord in `DATABASE_URL` moeten gelijk zijn. Bestaat de database al met een ander wachtwoord, gebruik dan `docker compose down -v` (wist alle gegevens). |
| "Geen AI-model ingesteld" | Ollama draait niet of het model ontbreekt | Start Ollama, controleer met `ollama list` en doe `ollama pull qwen3:8b` |
| Cv-herkenning blijft hangen | Worker draait niet of Ollama is traag | `docker compose logs -f worker`. De eerste aanroep laadt het model in het geheugen en duurt langer. |
| Matchscore "onvoldoende gegevens" | Profiel te leeg | Vul vaardigheden en werkervaring aan en stel je voorkeuren in |
| Geen verificatiemail | E-mails gaan naar Mailpit | Open http://localhost:8325 |
| Werkgever kan niet publiceren | E-mail niet bevestigd | Klik op de link in Mailpit |
| "Gescande PDF" | De PDF bevat een afbeelding van tekst | Upload een tekst-PDF of DOCX, of vul je profiel met de hand in |
| Demovacatures missen voordelen of procedure | Ze werden gemaakt vóór die velden bestonden | `docker compose exec api python -m app.cli seed-demo` vult ze één keer aan |
| Poort al in gebruik | Een ander programma gebruikt 3300, 8300, 5436 of 8325 | Stop dat programma of pas de poort aan in `docker-compose.yml` |
| Demowachtwoord vergeten | Wordt niet opgeslagen | Gebruik *Wachtwoord vergeten* op de inlogpagina; de mail komt in Mailpit |

---

## 16. Privacy en veiligheid

- Wachtwoorden worden gehasht met **Argon2id**; sessies staan in de database, met een `HttpOnly`-cookie en CSRF-bescherming.
- Rollen worden altijd **door de server** bepaald, nooit door de browser.
- Cv-bestanden staan in een **privémap** en worden nooit rechtstreeks geserveerd. Uploads worden gecontroleerd op echt
  bestandstype en grootte.
- Werkgevers zien enkel het cv dat een kandidaat **uitdrukkelijk deelt** voor die vacature.
- Bedrijven zijn van elkaar afgeschermd: je kan enkel je eigen vacatures en kandidaten beheren.
- Tekst uit cv's en vacatures wordt naar de AI gestuurd als *onbetrouwbare gegevens*. Instructies erin worden genegeerd
  (bescherming tegen prompt injection).
- Gebruikers kunnen hun gegevens exporteren en hun account verwijderen.

Meer in [docs/security.md](docs/security.md). **Let op:** de privacyverklaring en de voorwaarden zijn technische
ontwerpen en moeten juridisch nagekeken worden vóór een publieke lancering.

---

## 17. Beperkingen en volgende stappen

- De kwaliteit van de cv-herschrijving hangt af van het model. `qwen3:8b` herkent goed, maar herschrijft eerder bescheiden.
  Een groter model geeft betere teksten; de feitencontrole blijft dezelfde.
- Geen OCR voor gescande PDF's.
- De interface is enkel in het Nederlands. Franse en Engelse vertalingen moeten nog geschreven worden; cv's kunnen wel in
  NL, FR en EN gemaakt worden.
- Rate limiting zit per API-proces in het geheugen. Bij meerdere servers moet dat naar Redis.
- Er is nog geen productie-installatie (TLS, back-ups, monitoring, een echte SMTP-dienst).
- Meldingen zijn enkel in de app; e-mail wordt alleen gebruikt voor verificatie en wachtwoordherstel.

---

## 18. Woordenlijst

| Term | Betekenis |
|---|---|
| **Matchscore** | Getal van 0 tot 100 dat aangeeft hoe goed een profiel bij een vacature past, met uitleg per onderdeel |
| **Harde eis** | Een vereiste die niet weggepoetst kan worden door de rest (taal, diploma …); beperkt de score tot 60 |
| **Embedding** | Een reeks getallen die de betekenis van een tekst weergeeft, gebruikt om inhoudelijke gelijkenis te meten |
| **Ollama** | Programma om AI-modellen lokaal op je eigen computer te draaien |
| **Worker** | Achtergrondproces dat lange taken uitvoert (cv lezen, optimaliseren …) |
| **Migratie** | Een script dat de databasestructuur bijwerkt (bv. een nieuwe kolom) |
| **Seed** | Voorbeeldgegevens die je in de database laadt om de app te testen |
| **Mailpit** | Testmailbox die alle e-mails opvangt, zodat er niets echt verstuurd wordt |
| **ATS** | *Applicant Tracking System*: software waarmee bedrijven cv's automatisch filteren |
| **Feitencontrole** | Controle die elke door AI herschreven zin toetst aan je echte profiel |

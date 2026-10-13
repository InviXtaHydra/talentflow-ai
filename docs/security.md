# Security and privacy

## Authentication and sessions

- Passwords: Argon2id (`argon2-cffi` defaults), min. 10 characters; rehashed when parameters change.
- Sessions: random 256-bit token in an `HttpOnly`, `SameSite=Lax` cookie (`Secure` in production); only a keyed hash
  (HMAC-SHA256 with `SECRET_KEY`) is stored. Sessions expire (`SESSION_TTL_HOURS`), can be listed and revoked, and all
  other sessions end after a password change or reset.
- E-mail verification and password reset use single-use, expiring tokens (stored hashed). Password reset answers the same
  way whether or not an account exists; login timing is equalized with a dummy hash.
- Roles (`candidate`, `employer`, `admin`) are set by the server. Registration only allows candidate/employer; admins are
  created with `python -m app.cli create-admin`.
- Rate limits: registration, login (per IP and per e-mail), password reset, verification, CV optimization and the assistant.

## CSRF and browser hardening

Double-submit token (`tf_csrf` cookie echoed as `X-CSRF-Token`, bound to the session when logged in), an `Origin` check
and `SameSite=Lax` cookies. Security headers on API and frontend: `X-Content-Type-Options`, `Referrer-Policy`,
`X-Frame-Options`, `Permissions-Policy`. API responses are `Cache-Control: no-store`.

## Authorization

Every protected route depends on the current user and role; object access is checked in the services:
- CV documents, versions, optimizations, applications, notifications and tasks are filtered by owner. Other users get **404**.
- Company data and applicants are only available to members of that company (`require_member`), admins excepted.
- Employers only see applications made **through the platform** to their own vacancies, and only the CV version the
  candidate selected with explicit consent. External applications a candidate tracks stay private.

Covered by tests: `test_auth.py`, `test_jobs.py`, `test_cv_processing.py`, `test_optimization.py`, `test_applications.py`,
`test_privacy_and_worker.py`.

## Uploads and files

- Type detection by content (PDF magic bytes; DOCX zip structure), extension must match, macro-enabled documents and
  zip bombs are rejected, configurable size limits (`MAX_UPLOAD_MB`, `MAX_LOGO_MB`).
- Files are stored outside any web root under random 48-hex-character keys (permissions 600) and only served through
  authorized endpoints with `Content-Disposition` and `nosniff`.
- Document content is treated as data: nothing is executed or followed; it reaches the model only inside delimited tags.

## Logging and audit

Logs contain identifiers and outcomes, never CV text, passwords, tokens or e-mail bodies; a log filter additionally masks
anything that looks like a secret or an e-mail address. `ai_usage_records` stores operation, model, duration and token
counts, not prompts or answers. `audit_logs` records security-relevant events (login, registration, password changes,
CV uploads/deletions, optimizations, application status changes, admin actions, data exports, account deletion) with a
keyed hash of the IP address.

## GDPR support

- Data minimization: only what the features need; matching never uses sensitive characteristics.
- Transparency: privacy notice (`/privacy`), explanation of every match, visible labelling of demo data and simulated results.
- Access/portability: `GET /account/export` (JSON with all personal data).
- Erasure: delete a CV document (file + extracted data) or the whole account (all rows cascade, files are deleted).
- Retention: expired sessions/tokens and old operational records are deleted daily; optional automatic deletion of
  inactive accounts (`INACTIVE_ACCOUNT_RETENTION_DAYS`).
- AI processing: local by default (no CV data leaves the server). Using a hosted provider requires a data-processing
  agreement and an updated privacy notice.

**Not covered by the software (organizational/legal work):** a lawful basis and records of processing, a DPA with every
processor (hosting, SMTP, any AI provider), a DPIA for automated matching, the final privacy notice and terms, a breach
procedure, and the retention periods themselves. Technical measures alone do not make the platform compliant.

## Dependency checks

`npm audit --omit=dev` and `pip-audit -r backend/requirements.txt` reported no known vulnerabilities at the time of writing.
Run them regularly.

## Production checklist

- `APP_ENV=production` (Secure cookies, no API docs), a strong `SECRET_KEY`, unique database credentials.
- TLS termination in front of the frontend; only the frontend exposed publicly.
- A real SMTP provider; backups of the database and the storage volume; monitoring of the worker and failed tasks.
- With several API processes: move rate limiting to a shared store (Redis).

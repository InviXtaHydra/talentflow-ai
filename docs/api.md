# API

Base path: `/api/v1`. Interactive documentation: `http://localhost:8300/docs` (disabled when `APP_ENV=production`).

## Conventions

- **Authentication**: session cookie `tf_session` (HttpOnly). Obtain it with `POST /auth/register` or `POST /auth/login`.
- **CSRF**: every `POST/PUT/PATCH/DELETE` must send `X-CSRF-Token` equal to the `tf_csrf` cookie (call `GET /auth/csrf`
  once when there is no cookie yet). For logged-in users the token is bound to the session.
- **Errors**: `{"error": {"code": "…", "message": "…", "details": …}}` with a fitting HTTP status (401, 403, 404, 409, 413,
  415, 422, 429, 502/503 for AI provider problems).
- **Pagination**: `?page=&page_size=` → `{items, total, page, page_size, pages}`.
- Objects of other users are reported as **404** (not 403), so their existence is not revealed.

## Endpoints

| Area | Endpoints |
|---|---|
| Health | `GET /health`, `GET /health/ready`, `GET /config` |
| Auth | `GET /auth/csrf`, `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `POST /auth/verify-email`, `POST /auth/resend-verification`, `POST /auth/forgot-password`, `POST /auth/reset-password`, `POST /auth/change-password`, `GET /auth/sessions`, `DELETE /auth/sessions/{id}` |
| Account / privacy | `PATCH /account`, `GET /account/export`, `POST /account/delete` |
| Candidate | `GET/PATCH /candidates/me`, `GET/PUT /candidates/me/preferences`, `GET /candidates/me/dashboard`, `POST /candidates/me/matches/recalculate` |
| CV documents | `POST /cvs/upload`, `GET /cvs`, `GET /cvs/{id}`, `GET /cvs/{id}/file`, `POST /cvs/{id}/confirm`, `POST /cvs/{id}/retry-extraction`, `POST /cvs/{id}/analyze`, `GET /cvs/{id}/versions`, `DELETE /cvs/{id}` |
| CV analysis | `POST /cv-analyses` (profile), `GET /cv-analyses` |
| CV versions | `GET/POST /cv-versions`, `GET/PATCH/DELETE /cv-versions/{id}`, `POST /cv-versions/{id}/duplicate`, `POST /cv-versions/{id}/export` |
| Optimization | `POST /jobs/{id}/optimize-cv` → 202 `{optimization_id, task_id}`, `GET/PATCH /cv-optimizations/{id}`, `POST /cv-optimizations/{id}/restore`, `POST /cv-optimizations/{id}/regenerate`, `POST /cv-optimizations/{id}/export` |
| Jobs | `GET /jobs` (search, filters, sort, pagination), `GET /jobs/facets`, `GET /jobs/recommendations`, `GET /jobs/saved`, `GET /jobs/compare?ids=`, `GET /jobs/{id}`, `GET /jobs/{id}/related`, `GET /jobs/{id}/match`, `POST/DELETE /jobs/{id}/save`, `PATCH /jobs/{id}` |
| Companies | `GET /companies`, `POST /companies`, `GET/PATCH /companies/{id}`, `GET /companies/{id}/jobs`, `POST /companies/{id}/jobs`, `POST/GET /companies/{id}/logo`, `GET/POST /companies/{id}/members`, `DELETE /companies/{id}/members/{user_id}` |
| Applications | `POST /applications`, `GET /applications/me`, `GET/PATCH/DELETE /applications/{id}` |
| Employer | `GET /employer/dashboard`, `GET /employer/applications`, `GET/PATCH /employer/applications/{id}`, `GET /employer/applications/{id}/cv` |
| Notifications | `GET /notifications`, `GET /notifications/unread-count`, `POST /notifications/read` |
| Tasks | `GET /tasks/{id}`, `POST /tasks/{id}/cancel` |
| Assistant | `GET/POST/DELETE /assistant/messages` |
| Admin | `GET /admin/stats`, `GET /admin/users`, `PATCH /admin/users/{id}`, `GET /admin/jobs`, `POST /admin/jobs/{id}/close`, `GET /admin/audit-logs`, `POST /admin/job-feeds/import` |

### Job search parameters

`q`, `company_id`, `city`, `max_distance_km` (with `city`), `remote[]`, `employment_type[]`, `experience_level[]`,
`industry[]`, `skills[]`, `language[]`, `salary_min_annual` (EUR per year; vacancies without a salary are excluded),
`sort` = `relevance | date | salary | match`, `page`, `page_size`.

### Export

`POST …/export` with `{"format": "pdf" | "docx", "template": "modern" | "minimal" | "technical", "preview": false}`
returns the file with a `Content-Disposition` filename like `CV_Firstname_Lastname_Job_Title.pdf`.

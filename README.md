# Moodle-agnostic LTI Admin Transfer Tool (Moodle → Azure Blob) — Railway PoC

This refactor makes the app **Moodle-agnostic** by removing global Moodle tokens and using **per-issuer onboarding** plus **per-admin OAuth2** to call Moodle Web Services. Any Moodle that can launch LTI 1.3 and has OAuth2 enabled can connect without pre-provisioned tokens.

## Highlights
- **LTI 1.3 admin launch** validates the platform JWT and discovers the issuer.
- **Per-issuer setup UI**: first launch from a new Moodle prompts for **OAuth2 client id/secret** and auth/token endpoints (defaults provided).
- **Per-admin OAuth2**: after setup, each admin is asked once to authorise API access; tokens (access+refresh) are stored per `(issuer, user)`.
- **Moodle file listing** uses OAuth bearer to call `core_course_get_contents`.
- **Azure Blob uploads** stream data using SAS (supports large files; keep within ~2GB on Railway).
- **Background worker** with RQ + Redis.
- **Railway-ready**: `Procfile`, `requirements.txt`, `railway.json`.

> Note: Each Moodle needs an OAuth2 client for your app in order to authorise API access. This is a one-time admin action on that Moodle instance. LTI and OAuth are separate: LTI provides launch trust; OAuth provides API consent.

---

## Deploy on Railway
1. Create a project and deploy this repo (ZIP or GitHub).
2. Provision **PostgreSQL** and **Redis** plugins and set env vars:
   - `DATABASE_URL`, `REDIS_URL`
3. Set app env:
   - `SESSION_SECRET`
   - `AZURE_STORAGE_ACCOUNT`, `AZURE_STORAGE_KEY`, `AZURE_BLOB_CONTAINER`
   - `APP_BASE_URL` → your Railway web URL.
4. Two services from this repo:
   - **Web** (`Procfile:web`)
   - **Worker** (`python -m app.worker`)

Healthcheck: `GET /healthz` → `{"ok": true}`.

---

## First launch from a new Moodle (issuer)
1. Register your **LTI 1.3 Tool** in that Moodle (normal process).
2. Launch the tool as an **Admin/Instructor** from any course.
3. The app will present **Platform Setup** for that issuer:
   - Enter the OAuth **Client ID** and **Client Secret** you created in that Moodle for your app.
   - Confirm the **Authorisation Endpoint** and **Token Endpoint**. Defaults assume:
     - `https://<moodle>/oauth2/authorize.php`
     - `https://<moodle>/oauth2/token.php`
4. You’ll then be redirected to the Moodle **consent screen** to grant your app access to Web Services.

> If your Moodle requires a specific OAuth scope for web services, configure it in Moodle; this PoC requests scope `webservice` by default (adjust in code if needed).

---

## Using the app
- `/ui` — simple picker to enter `course_id`, list files, select, and send to Azure.
- `/moodle/files?course_id=NN` — uses bearer token to call `core_course_get_contents`.
- `/transfers` — enqueues a background job per selection; status is polled until complete.

---

## Data model
- `platforms` — per-issuer config (OAuth client creds, endpoints).
- `user_tokens` — per `(issuer, user)` access+refresh tokens.
- `transfer_jobs` / `transfer_events` — audit and progress.

---

## Limits & next steps
- OAuth endpoints differ between Moodle versions/configs — the setup UI lets admins override defaults.
- For production, add: CSRF/state hardening, nonce, PKCE, better error UX, virus scanning, checksums, delivery receipts, and retries/backoff telemetry.

MIT — enjoy.

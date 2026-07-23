# ssd-prac

Docker Compose stack with an HTTPS web server (Basic Auth) fronting a Flask
search application, a Postgres database, and a local Gitea git server.

## Services

### `web` — Nginx (HTTPS + Basic Auth, reverse proxy)
- Served at **https://127.0.0.1/** using a self-signed certificate (`certs/server.crt` / `certs/server.key`, CN/SAN = `127.0.0.1`, valid until Oct 2028).
- `http://127.0.0.1/` redirects to HTTPS.
- Protected with HTTP Basic Auth:
  - Username: `admin`
  - Password: `2401807@SIT.singaporetech.edu.sg`
- Credentials are stored as an apr1-hashed entry in `web/.htpasswd` (not the plaintext password).
- Your browser/client will warn about the self-signed cert (`NET::ERR_CERT_AUTHORITY_INVALID` or similar) — this is expected; accept/trust it to proceed. With `curl`, use `-k`.
- All requests are reverse-proxied to the `app` service — nginx only handles TLS termination and Basic Auth.

To regenerate the certificate: see `certs/openssl.cnf` and re-run the `openssl req -x509 ...` command shown there.

### `app` — Flask search application
A small search form app, built from `app/` (`app/app.py`) and served through `web` at https://127.0.0.1/. Runs as a non-root user in the container.

- **Home page (`GET /`)**: a form with a single search-term input and a submit button.
- **Search (`POST /search`)**:
  - Protected by a CSRF token (`Flask-WTF`), rendered as a hidden field and required on every submission — requests without a valid token get `400`.
  - The input is validated both client-side (`app/static/js/validate.js`) and server-side (`app/validation.py`) per OWASP Proactive Control C3 (Validate All Input): length between 1–100 characters, an allow-list restricting the term to ASCII letters/digits/spaces, plus explicit SQL Injection / XSS signature checks for clearer rejection reasons. Client-side validation is UX only — the server check is the real security boundary. Unicode input is intentionally out of scope.
  - If the input fails validation (too short/long, or flagged as an attack), the input is cleared and the home page is re-rendered with an error message.
  - If the input passes validation, it is logged to the database and a results page is shown with the search term and a "Back to Home" button. Output is rendered through Jinja2 auto-escaping and the DB write uses a parameterized query, as defense in depth.

### `db` — Postgres
- Stores validated search queries in table `"2401807"` (`id`, `search_query`, `query_time`), created via `db/init.sql`.
- Not exposed to the host — only reachable by `app` on the internal Docker network.
- Inspect logged searches: `docker compose exec db psql -U ssd_user -d ssd_prac -c 'SELECT * FROM "2401807";'`

### `sonarqube` + `sonar-db` — local SonarQube
- Web UI: **https://127.0.0.1:9000/** (nginx terminates TLS with the same self-signed cert and proxies to the `sonarqube` container; SonarQube itself has no built-in HTTPS support, a reverse proxy is the documented way to serve it over TLS).
- Login: `admin` / `2401807@SIT.singaporetech.edu.sg`
  - **Note:** the exact password `2401807@sit.singaporetech.edu.sg` is rejected by SonarQube's built-in password policy (requires an uppercase character; this isn't a configurable setting in this version). `SIT` is capitalized as the minimal change to satisfy it.
- Findings for the search app (Q4) live under project key `ssd-prac-app`: https://127.0.0.1:9000/dashboard?id=ssd-prac-app
- Backed by its own Postgres instance (`sonar-db`), separate from the app's `db` service.

First boot takes 1–3 minutes (Elasticsearch + DB migrations). Poll `https://127.0.0.1:9000/api/system/status` (`-k`) until it reports `{"status":"UP"}`, then run once:

```bash
bash scripts/setup-sonarqube-account.sh
```

### Running a scan (Q8)

```bash
bash scripts/run-sonar-scan.sh
```

Runs the `sonarsource/sonar-scanner-cli` Docker image against `app/` (config: `app/sonar-project.properties`), attached to the compose network so it talks to SonarQube over `http://sonarqube:9000` directly (no need to trust the self-signed cert for the scan itself — results still show up on the HTTPS UI). A fresh scanner token is generated via the API for each run.

Current result: **0 Bugs, 0 Vulnerabilities, 0 Security Hotspots, 0 Code Smells** (Q9). One SonarQube finding (`python:S2068`, on `app.py`'s `SECRET_KEY` config line) was a false positive — Sonar's secret-detection pattern matched the *name* `SECRET_KEY`, not an actual literal value (the code reads it from an environment variable or falls back to a freshly generated random key, never a hardcoded string). It's resolved as `FALSE-POSITIVE` in SonarQube with a comment explaining why, rather than obscured in code to dodge the scanner. Everything else was a real, fixed issue:

| Rule | Issue | Fix |
|---|---|---|
| `python:S8392` (Blocker) | Flask dev server bound to `0.0.0.0` | Bound to `127.0.0.1` instead — this code path (`app.run(...)`) is only used for local/CI runs where the test client is always on the same host; the real container entrypoint is gunicorn's own `-b 0.0.0.0:5000`, unaffected |
| `python:S4502` (Critical) | No CSRF protection on the POST form | Added `Flask-WTF` `CSRFProtect` + a hidden `csrf_token` field |
| `docker:S6470` (Critical) | `COPY . .` could pull in unintended files | Replaced with explicit per-file/per-directory `COPY` instructions, plus an `app/.dockerignore` |
| `docker:S6471` (Minor) | Container ran as root | Added a dedicated non-root `appuser` |

### `gitea` — local Git server
- Web UI: http://127.0.0.1:3000/
- Git SSH clone port: `2222` (mapped from container port 22)
- Data persisted in `gitea/data/` (gitignored)

After the first `docker compose up -d`, run **once** to provision the account:

```bash
bash scripts/setup-gitea-account.sh
```

This creates the Gitea admin account:
- Username: `GohZhenAnErnest` (Gitea usernames can't contain spaces)
- Full name: `Goh Zhen An Ernest`
- Email: `2401807@sit.singaporetech.edu.sg`
- Password: `2401807@sit.singaporetech.edu.sg`

The local repo's git identity (`git config user.name` / `user.email`, used for commit authorship) is also set to `Goh Zhen An Ernest` / `2401807@sit.singaporetech.edu.sg` for this repository.

## Usage

From the repository root:

```bash
sudo docker-compose up
```

This builds the `app` image and starts all services (`web`, `app`, `db`, `sonarqube`, `sonar-db`, `gitea`) in the foreground. No prior setup is required — the TLS certificate, htpasswd file and database schema are already included in the repo, and Postgres/SonarQube/Gitea initialize themselves on first boot. SonarQube takes 1–3 minutes and Gitea ~20–30 seconds to finish first-run initialization; the other services are ready almost immediately.

(`sudo` is only necessary on Linux/macOS when your user isn't in the `docker` group. On Docker Desktop for Windows/Mac it isn't needed and can be omitted. `docker-compose` and the newer `docker compose` are interchangeable here — both were tested against this stack.)

To run detached and provision the Gitea + SonarQube accounts:

```bash
sudo docker-compose up -d
bash scripts/setup-gitea-account.sh       # first run only
bash scripts/setup-sonarqube-account.sh   # first run only, after SonarQube reports status UP
```

- Website / search app: https://127.0.0.1/ (login `admin` / `2401807@SIT.singaporetech.edu.sg`)
- SonarQube: https://127.0.0.1:9000/ (login `admin` / `2401807@SIT.singaporetech.edu.sg`)
- Git server: http://127.0.0.1:3000/ (login `GohZhenAnErnest` / `2401807@sit.singaporetech.edu.sg`)

```bash
sudo docker-compose down
```

## CI (GitHub Actions)

`.github/workflows/ci.yml` runs on every push/PR to `main` (and manually via `workflow_dispatch`):

- **Dependency Check** — `pypa/gh-action-pip-audit` scans `app/requirements.txt` for known Python vulnerabilities.
- **ESLint Security Scan** — lints `app/static/js` with [`eslint-plugin-security`](https://github.com/eslint-community/eslint-plugin-security) (unsafe `eval`, non-literal `RegExp`/`require`, etc.) and [`eslint-plugin-no-unsanitized`](https://github.com/mozilla/eslint-plugin-no-unsanitized) (DOM XSS sinks like `innerHTML`). Config: `eslint.config.js`. Run locally with `npm install && npm run lint:security`.
- **Integration & UI Tests (HTTP)** — runs after both checks above pass; starts the Flask app directly over HTTP against a Postgres service container and runs `tests/test_integration.py` (HTTP + DB assertions) and `tests/test_ui.py` (Playwright/Chromium, including a JS-disabled test proving server-side validation holds independently of the client).

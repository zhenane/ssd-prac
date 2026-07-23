# ssd-prac

Docker Compose stack with an HTTPS web server (Basic Auth) fronting a Flask
search application, a Postgres database, and a local Gitea git server.

## Services

### `web` — Nginx (HTTPS + Basic Auth, reverse proxy)
- Served at **https://127.0.0.1/** using a self-signed certificate (`certs/server.crt` / `certs/server.key`, CN/SAN = `127.0.0.1`, valid until Oct 2028).
- `http://127.0.0.1/` redirects to HTTPS.
- Protected with HTTP Basic Auth:
  - Username: `admin`
  - Password: `2401807@sit.singaporetech.edu.sg`
- Credentials are stored as an apr1-hashed entry in `web/.htpasswd` (not the plaintext password).
- Your browser/client will warn about the self-signed cert (`NET::ERR_CERT_AUTHORITY_INVALID` or similar) — this is expected; accept/trust it to proceed. With `curl`, use `-k`.
- All requests are reverse-proxied to the `app` service — nginx only handles TLS termination and Basic Auth.

To regenerate the certificate: see `certs/openssl.cnf` and re-run the `openssl req -x509 ...` command shown there.

### `app` — Flask search application
A small search form app, built from `app/` (`app/app.py`) and served through `web` at https://127.0.0.1/.

- **Home page (`GET /`)**: a form with a single search-term input and a submit button.
- **Search (`POST /search`)**:
  - The input is validated both client-side (`app/static/js/validate.js`) and server-side (`app/validation.py`) per OWASP Proactive Control C3 (Validate All Input): length between 1–100 characters, an allow-list restricting the term to ASCII letters/digits/spaces, plus explicit SQL Injection / XSS signature checks for clearer rejection reasons. Client-side validation is UX only — the server check is the real security boundary. Unicode input is intentionally out of scope.
  - If the input fails validation (too short/long, or flagged as an attack), the input is cleared and the home page is re-rendered with an error message.
  - If the input passes validation, it is logged to the database and a results page is shown with the search term and a "Back to Home" button. Output is rendered through Jinja2 auto-escaping and the DB write uses a parameterized query, as defense in depth.

### `db` — Postgres
- Stores validated search queries in table `"2401807"` (`id`, `search_query`, `query_time`), created via `db/init.sql`.
- Not exposed to the host — only reachable by `app` on the internal Docker network.
- Inspect logged searches: `docker compose exec db psql -U ssd_user -d ssd_prac -c 'SELECT * FROM "2401807";'`

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

This builds the `app` image and starts all four services (`web`, `app`, `db`, `gitea`) in the foreground. No prior setup is required — the TLS certificate, htpasswd file and database schema are already included in the repo, and Postgres/Gitea initialize themselves on first boot. Gitea takes ~20–30 seconds to finish its first-run initialization; the other three services are ready almost immediately.

(`sudo` is only necessary on Linux/macOS when your user isn't in the `docker` group. On Docker Desktop for Windows/Mac it isn't needed and can be omitted. `docker-compose` and the newer `docker compose` are interchangeable here — both were tested against this stack.)

To run detached and provision the Gitea account (username `GohZhenAnErnest`, see below):

```bash
sudo docker-compose up -d
bash scripts/setup-gitea-account.sh   # first run only
```

- Website / search app: https://127.0.0.1/ (login `admin` / `2401807@sit.singaporetech.edu.sg`)
- Git server: http://127.0.0.1:3000/ (login `GohZhenAnErnest` / `2401807@sit.singaporetech.edu.sg`)

```bash
sudo docker-compose down
```

## CI (GitHub Actions)

`.github/workflows/ci.yml` runs on every push/PR to `main` (and manually via `workflow_dispatch`):

- **Dependency Check** — `pypa/gh-action-pip-audit` scans `app/requirements.txt` for known Python vulnerabilities.
- **ESLint Security Scan** — lints `app/static/js` with [`eslint-plugin-security`](https://github.com/eslint-community/eslint-plugin-security) (unsafe `eval`, non-literal `RegExp`/`require`, etc.) and [`eslint-plugin-no-unsanitized`](https://github.com/mozilla/eslint-plugin-no-unsanitized) (DOM XSS sinks like `innerHTML`). Config: `eslint.config.js`. Run locally with `npm install && npm run lint:security`.
- **Integration & UI Tests (HTTP)** — runs after both checks above pass; starts the Flask app directly over HTTP against a Postgres service container and runs `tests/test_integration.py` (HTTP + DB assertions) and `tests/test_ui.py` (Playwright/Chromium, including a JS-disabled test proving server-side validation holds independently of the client).

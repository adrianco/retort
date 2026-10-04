# Summary: rest-api-crud-76 · python/codex/gpt-6-luna/neutral · rep 5

- **Shape:** Pure-stdlib Python REST API (`http.server.ThreadingHTTPServer`) backed by SQLite — no web framework, no third-party dependencies.
- **Structure:** 1 application module (`app.py`), 1 test module (`test_app.py`), plus `README.md`.
- **Interfaces:** 6 HTTP routes (POST/GET/GET-by-id/PUT/DELETE on `/books`, plus `GET /health`); 1 `books` SQLite table.
- **Notable:** Handler is a closure-parameterized `BaseHTTPRequestHandler` subclass (`create_handler(db_path)`), which makes it unit-testable without binding a socket. Tests exercise the validation/route-parsing/DB layers directly but never drive the HTTP dispatch end-to-end (the sandbox blocked socket binding), leaving `do_*` handlers untested (test_coverage=0.48).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

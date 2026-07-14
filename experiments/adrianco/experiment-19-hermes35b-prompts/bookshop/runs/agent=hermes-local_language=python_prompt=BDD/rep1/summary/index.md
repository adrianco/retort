# Summary: agent=hermes-local language=python prompt=BDD · rep 1

- **Shape:** Flask REST API backed by raw `sqlite3` (no ORM), single-module app.
- **Structure:** 1 app module, 1 test module (19 tests), plus README.
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`), 1 SQLite table, no CLI/library API.
- **Notable:** Tests fully embody the BDD prompt — 6 `Feature` classes of Given-When-Then scenarios exercising only the HTTP/JSON surface. `init_db()` runs on every request via `before_request`; `?author=` filter is a `LIKE` partial match.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

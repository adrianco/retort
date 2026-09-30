# Summary: effort=max·python·claude-sonnet-5-5·neutral · rep 3

- **Shape:** Standard-library WSGI REST API (PEP 3333, `wsgiref`) with a SQLite store — zero third-party runtime dependencies.
- **Structure:** 6 source modules + 1 package entry, 4 test modules + conftest (115 test functions).
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), 1 CLI entry point (`bookapi`), a `BookRepository` data layer over a `books` table.
- **Notable:** Unusually rigorous for the task — HEAD support, chunked/oversized-body rejection, log-injection escaping, Unicode-normalised case-insensitive author filter, threaded server. Uses only the stdlib rather than Flask/FastAPI.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

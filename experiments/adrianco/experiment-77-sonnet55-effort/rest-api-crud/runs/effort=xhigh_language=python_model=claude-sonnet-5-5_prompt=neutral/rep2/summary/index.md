# Summary: rest-api-crud · effort=xhigh, python, claude-sonnet-5-5, neutral · rep 2

- **Shape:** Pure Python stdlib WSGI REST API (`bookapi` package) with SQLite storage; served via `wsgiref` threading server, no third-party runtime deps.
- **Structure:** 6 source modules, 5 test files (62 test functions total) plus a shared conftest with an in-process WSGI test client.
- **Interfaces:** 6 HTTP routes (health + full CRUD with `?author=` filter), 1 CLI entry point (`python -m bookapi`, host/port/db flags), and a small library API (`BookApp`, `BookStore`, `validate_book`, `create_server`).
- **Notable:** Clean separation of routing (app), storage (db), validation, and server wiring; thread-safe single-connection store with a lock; extras beyond the spec — request body size cap (413), 405 with `Allow` header, registered `casefold` SQL function for non-ASCII author matching, 64-bit id range guarding, and partial PUT updates.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

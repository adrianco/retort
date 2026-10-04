# Summary: rest-api-crud · effort=high language=python model=claude-opus-5-5 prompt=neutral · rep1

- **Shape:** Pure-stdlib Python REST API — hand-rolled WSGI app (`wsgiref`) with a SQLite-backed store, no web framework or third-party dependencies.
- **Structure:** 5 source modules (`app`, `store`, `validation`, `__main__`, `__init__`) + 2 test files (33 test functions) with a shared `conftest.py`.
- **Interfaces:** 6 HTTP routes (health + full CRUD with `?author=` filter), a `python -m bookapi` CLI (host/port/db flags), and a small library API (`create_app`, `BookAPI`, `BookStore`, `validate_book`).
- **Notable:** Unusually thorough for the task — a threaded WSGI server, single lock-guarded shared connection for `:memory:` safety, exhaustive validation (surrogate/UTF-8, bool-vs-int year, oversized-ID guard), HEAD/trailing-slash/405 handling, and both in-process and real-socket test suites (concurrency + persistence). No external framework used.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

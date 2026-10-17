# Architecture summary — books_api

A stdlib-only REST API (no third-party runtime deps) in three layers, plus a CLI
entry point.

## Modules

| Module | Role |
|--------|------|
| `books_api/server.py` | HTTP layer. `BookAPIHandler` (on `ThreadingHTTPServer`) routes `/health`, `/books`, `/books/{id}` via a regex, dispatches by method, and maps exceptions to JSON + status codes. `create_server()` factory; port 0 → OS-assigned. |
| `books_api/database.py` | Storage. `BookRepository` wraps one shared `sqlite3` connection guarded by an `RLock` (threaded server). CRUD + `find(author=)` + `ping()`. Unique-ISBN violations surface as `ConflictError`. |
| `books_api/validation.py` | Input validation. `validate_book()` enforces required `title`/`author`, optional `year` (int, bounded), optional `isbn` (ISBN-10/13 format + checksum, normalised). Raises `ValidationError` with a per-field error map. |
| `books_api/__main__.py` | CLI: `python -m books_api` with `--host/--port/--db`. |

## Request flow

`do_* → _dispatch(method)` → route match → handler (`_create_book`, `_list_books`,
`_get_book`, `_update_book`, `_delete_book`, `_health`). Handlers call the repository
and `_send_json`. Errors raise `HTTPError`/`ValidationError`/`ConflictError`, caught
centrally in `_dispatch` and rendered as JSON (400/404/405/409/413/500/503).

## Tests

- `tests/conftest.py` — spins a real server on a free port with an in-memory DB; `api` fixture issues real HTTP requests.
- `tests/test_api.py` — HTTP-level coverage of every endpoint, status code, and error path.
- `tests/test_repository.py` — storage layer incl. file persistence across connections.
- `tests/test_validation.py` — validation rules (parametrized).

51 test cases, all passing; `test_coverage=0.94`.

# Architecture summary

Stdlib-only Python REST service (`http.server` + `sqlite3`), no third-party runtime deps.

## Modules

- **`src/app.py`** — HTTP layer. `make_handler(repo)` returns a `BaseHTTPRequestHandler`
  subclass dispatching `do_GET/do_POST/do_PUT/do_DELETE`. Routes: `/health`, `/books`,
  `/books/{id}` (regex `BOOK_ID_RE`). Helpers `_send`/`_error`/`_read_json`/`_validated_body`
  centralise JSON I/O, body-size cap (1 MiB), and error shaping. `create_server()` wires a
  `ThreadingHTTPServer`; `main()` is a CLI entry point (`--host/--port/--db`).
- **`src/db.py`** — `BookRepository`, a thread-safe (single `threading.Lock`) wrapper over a
  SQLite connection with `check_same_thread=False`. CRUD: `create/list/get/update/delete`,
  `list(author=...)` for the filter. Schema created idempotently on init.
- **`src/validation.py`** — `validate_book(payload)` raises `ValidationError(errors)`; enforces
  required non-empty `title`/`author`, optional integer `year` 0–9999, optional 10/13-char ISBN.

## Flow

Request → handler routing → `_validated_body()` (POST/PUT) → `BookRepository` (locked SQLite
call) → `_send(status, json)`. 404 for unknown routes / missing ids; 422 for validation
failures; 400 for malformed JSON.

## Tests

`tests/conftest.py` spins a real server on an ephemeral port with a per-test tmp SQLite db and
a small urllib `Client`. `tests/test_api.py` — 8 integration tests covering health, CRUD,
author filter, validation, malformed JSON, and unknown routes.

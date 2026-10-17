# Architecture Summary: bookapi

A stdlib-only Python REST API for a book collection. No runtime dependencies
(`http.server` + `sqlite3`); `pytest` only for tests.

## Modules

| Module | Responsibility | Key symbols |
|--------|----------------|-------------|
| `bookapi/server.py` | HTTP layer: routing, JSON encoding, status codes | `BookRequestHandler`, `create_server`, `_dispatch`, `_route` |
| `bookapi/storage.py` | SQLite persistence, thread-safe | `BookStore` (`create`/`get`/`list`/`update`/`delete`/`ping`) |
| `bookapi/validation.py` | Payload validation / normalisation | `validate_book`, `ValidationError` |
| `bookapi/__main__.py` | CLI entry point (`python -m bookapi`) | `main` (argparse: `--host/--port/--db`) |
| `bookapi/__init__.py` | Public package surface | re-exports the three above |

## Interfaces / flow

- `create_server(host, port, db_path)` builds a `ThreadingHTTPServer` and attaches a `BookStore`.
- `_dispatch` parses the path into segments and routes `/health`, `/books`, `/books/{id}` to `_route`, which enforces the allowed-method set (JSON 405 + `Allow` header otherwise) and translates `ValidationError`/`_BadRequest` into JSON error responses.
- Handlers call into `BookStore`; every store method holds a single `threading.Lock` around the shared connection (`check_same_thread=False`), serialising DB access.
- `validate_book` requires non-blank string `title`/`author`, treats `year` (1..current+1, rejects bool) and `isbn` as optional; returns a normalised dict.

## Notes

- PUT is a full replacement (unset optional fields become null) — a defensible REST interpretation.
- Author filter is a case-insensitive exact match (`LOWER(author) = LOWER(?)`).
- `/health` pings the DB and returns 503 if the connection is unusable.

# Architecture summary — bookapi

Stdlib-only Python REST service (no third-party runtime deps), cleanly layered so the
API logic is testable without opening a socket.

## Modules

| Module | Responsibility |
|--------|----------------|
| `bookapi/models.py` | `BookFields` (validated attrs) and `Book` (adds `id`, `to_dict()`), frozen dataclasses. |
| `bookapi/validation.py` | `validate_book()` — required title/author, optional year (range-checked) and ISBN-10/13 (checksum-validated). Collects all errors before raising `ValidationError`. |
| `bookapi/repository.py` | `BookRepository` — SQLite CRUD. One shared connection guarded by an `RLock`; `AUTOINCREMENT` id, `COLLATE NOCASE` author with an index; `ping()` for health. |
| `bookapi/api.py` | `BookApi.handle(method, target, body) -> Response` — transport-independent routing via regex table. Maps `ApiError`/`ValidationError` to statuses; catch-all 500. |
| `bookapi/server.py` | `BookHTTPServer` (ThreadingHTTPServer) + handler bridging stdlib HTTP to `BookApi`. Enforces Content-Length limits, rejects Transfer-Encoding, 204 carries no body. |
| `bookapi/__main__.py` | `python -m bookapi` CLI: `--host/--port/--db`, wires repo→api→server. |

## Request flow

`BookHTTPServer` → `BookRequestHandler._dispatch` (reads bounded body) →
`BookApi.handle` (routes + error mapping) → handler → `BookRepository` (SQLite) →
`Response` serialized to JSON.

## Routes

`POST/GET /books`, `GET/PUT/DELETE /books/{id}`, `GET /health`. `?author=` filters the
list (case-insensitive exact match). Statuses: 201/200/204/400/404/405/413/500/503.

> Written inline by the evaluator; the standalone `run-summary` skill was not invoked
> separately in this session.

# Architecture Summary — bookapi (C)

A small, layered REST service in C11, no web framework — a hand-rolled HTTP/1.1
server over raw sockets, backed by SQLite.

## Modules

| File | Responsibility |
|------|----------------|
| `src/main.c` | Entry point: arg parsing (`--port`, `--db`), DB open, server loop wiring |
| `src/http.c/.h` | HTTP/1.1 parsing (request line, headers, body), query-string decode, response writing, socket accept loop |
| `src/api.c/.h` | Routing + endpoint handlers for `/`, `/health`, `/books`, `/books/{id}`; maps DB status → HTTP status/JSON |
| `src/db.c/.h` | SQLite persistence: schema (WAL, UNIQUE isbn), prepared-statement CRUD, list-with-author-filter, constraint classification (`DB_CONFLICT`) |
| `src/book_json.c/.h` | Book (de)serialisation, required-field validation (`title`, `author`) with structured field errors |
| `src/json.c/.h` | Minimal JSON parser (scalars, objects, arrays) |
| `src/strbuf.c/.h` | Growable string buffer + JSON-string escaping |

## Request flow

`accept()` → `http.c` parses request → `api_handle()` routes on method+path →
handler validates/parses body (`book_json`) → `db.c` executes prepared statement →
handler serialises result to JSON and sets status → `http.c` writes response.

## Notable design choices

- **Health check touches the DB** (`db_count`) so it reports `503` when storage is
  unavailable rather than a hollow `ok`.
- **PUT is full-replace** semantics; omitted fields are cleared.
- **Validation errors return `422`** with a `details[]` array of per-field messages.
- **ISBN uniqueness** enforced at the DB layer, surfaced as `409 isbn_conflict`.
- **Tests drive real TCP sockets** against the actual built binary, including a
  restart to prove durability.

# Architecture Summary

Single-file Python service (`app.py`, 184 LoC) using only the standard library
(`http.server.ThreadingHTTPServer` + `sqlite3`). No third-party dependencies.

## Modules / structure

- **`app.py`** — the whole service:
  - `init_db(path)` — creates the `books` table (id PK, title/author NOT NULL, year, isbn).
  - `validate(data)` — returns `(clean_dict, errors)`; requires non-empty `title`/`author`,
    type-checks `year` (int) and `isbn` (str).
  - `make_handler(db_path)` — closure over a `threading.Lock` and a per-request `db()`
    connection factory (`sqlite3.Row`), returning a `BaseHTTPRequestHandler` subclass.
    - Routing: `_route()` splits path/query; `_handle(method)` dispatches `/health`,
      `/books` (GET/POST), and `/books/{id}` (GET/PUT/DELETE) via regex.
    - Handlers: `_list` (with `?author=` filter), `_create`, `_get`, `_update`, `_delete`.
    - `_send(status, body)` writes JSON with Content-Type/Content-Length.
  - `create_server(host, port, db_path)` — inits DB, returns a ThreadingHTTPServer.
- **`test_app.py`** — 6 pytest tests using a real server on an ephemeral port + `urllib`.

## Interfaces (HTTP)

| Method | Path | Behavior |
|---|---|---|
| GET | /health | `{"status":"ok"}` 200 |
| POST | /books | create, 201 / 400 on validation |
| GET | /books | list, `?author=` filter |
| GET | /books/{id} | 200 / 404 |
| PUT | /books/{id} | full update, 200 / 400 / 404 |
| DELETE | /books/{id} | 204 / 404 |

## Flow / notable choices

- All DB access is serialized behind a single module-level `threading.Lock`, so the
  ThreadingHTTPServer is safe under concurrent requests.
- All SQL is parameterized (no string interpolation) — no injection surface.
- DB path is configurable via `BOOKS_DB`; port via `PORT`.

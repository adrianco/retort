# Architecture Summary

A single-file C REST service (`server.c`, 113 lines) backed by SQLite over a
blocking POSIX socket loop. No external framework — HTTP is parsed by hand.

## Modules / flow

- **`main`** — opens the SQLite DB (`BOOKS_DB` env, default `books.db`),
  creates the `books` table if absent, binds a TCP socket (`PORT` env, default
  8080), installs SIGINT/SIGTERM handlers, then accepts and serves one client
  at a time (synchronous, `Connection: close`).
- **`serve_client`** — reads the request header up to `\r\n\r\n`, parses the
  request line with `sscanf`, reads `Content-Length` (rejecting bodies over
  64 KiB with 413), splits the query string, then dispatches to `handle` and
  writes the HTTP response.
- **`handle`** — the router. Matches path+method to the six CRUD routes plus
  `/health`, returning a `{status, body}` struct with a JSON string body.
- **Helpers** — `escape_json` / `url_decode`, a hand-rolled `json_string` /
  `json_year` extractor (no JSON lib), `book_json` (row → JSON object),
  `get_id` (path → id).

## Data model

`books(id INTEGER PK AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL,
year INTEGER NOT NULL DEFAULT 0, isbn TEXT NOT NULL DEFAULT '')`. All DB access
uses prepared statements with bound params (no SQL injection surface).

## Tests

`test_api.py` (Python `unittest`, 4 test methods): 3 integration tests spawn the
compiled binary on a free port and exercise health/validation, create/list/
filter/get, and update/delete; 1 storage test exercises SQLite CRUD directly.

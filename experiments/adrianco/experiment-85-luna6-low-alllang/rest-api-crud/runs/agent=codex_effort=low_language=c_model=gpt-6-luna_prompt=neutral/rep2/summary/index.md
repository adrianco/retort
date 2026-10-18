# Architecture summary — book collection REST API (C)

Single-file service (`server.c`, 56 lines) using **GNU libmicrohttpd** for HTTP and
**SQLite** for persistence. Compiled to `book_server`; `test_server.c` reuses `server.c`
via `#define BOOKS_TEST` (which excludes `main`) and links the same helpers.

## Modules / flow

- **`main`** (server.c:55) — parses `--port`/`--db`, opens SQLite, creates the `books`
  table (`id` PK autoincrement, `title`/`author` NOT NULL, `year` default 0, `isbn`),
  installs SIGINT/SIGTERM handlers, starts the MHD daemon with `handler`, loops until stopped.
- **`handler`** (server.c:39) — the single MHD request callback. Accumulates the request
  body across MHD calls (`struct State`), then dispatches by `url`/`method`:
  `/health`, `/books` (GET list + `?author=` filter, POST create), `/books/{id}`
  (GET/PUT/DELETE), plus CORS `OPTIONS` and a 404 fallthrough.
- **JSON helpers** — `json_escape`/`json_string` (escaping), `serialize_book`
  (row → JSON object), `send_response`/`error_response` (JSON body + status + CORS header).
- **`parse_fields`** (server.c:25) — hand-rolled JSON object parser for `title`/`author`/
  `isbn`/`year`; tolerates missing keys and skips unknown ones.

## Interfaces

REST over HTTP, JSON request/response bodies, status codes 200/201/400/404/413/500/204.
Data access is direct parameterized `sqlite3_stmt` queries (no injection surface).

## Notes

- No end-to-end HTTP test; `test_server.c` exercises `parse_fields`, SQL CRUD and
  `serialize_book` directly (helper-level coverage).
- Fixed-size stack buffers (`char[4096]`/`char[20000]`) for serialization truncate
  pathologically long fields; `realloc` in the list route is unchecked.

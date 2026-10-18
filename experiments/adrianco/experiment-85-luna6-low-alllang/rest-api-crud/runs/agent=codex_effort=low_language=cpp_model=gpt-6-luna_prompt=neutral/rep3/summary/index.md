# Architecture Summary

Single-file C++17 service (`main.cpp`, 44 dense lines) plus a test harness (`tests.cpp`)
and a CMake build. No framework — a hand-rolled blocking TCP/HTTP/1.1 server.

## Modules / components

- **`Book` struct + JSON helpers** (`main.cpp:16-24`) — `trim`, `url_decode`, `encode`
  (via json-c), `book_json`, `error_json`, `parse_json`, `field` (typed JSON extraction).
- **`Store`** (`main.cpp:25-31`) — RAII wrapper over an SQLite `books` table
  (`id` PK autoincrement, `title`/`author` NOT NULL, `year`, `isbn`). Opened from
  `BOOKS_DB` env (default `books.db`).
- **`books_route`** (`main.cpp:32-39`) — the router/controller. Dispatches on
  `(method, path)` for `/health`, `/books` (GET list + ?author=, POST), and
  `/books/{id}` (GET/PUT/DELETE). Uses prepared statements for all DB access.
- **HTTP layer** (`main.cpp:41-44`) — `read_request` parses request line + headers +
  Content-Length body; `serve_client` writes the status line, JSON content-type, and
  body; `main` binds `PORT` (default 8080) and serves one connection at a time.

## Request flow

`accept` → `read_request` (parse method/path/query/body) → `books_route` (DB op, builds
JSON + status) → `serve_client` (HTTP response) → `close`. Single-threaded, one request
per connection (`Connection: close`).

## Tests

`tests.cpp` `#include`s `main.cpp` with `main` macro-renamed, then exercises `books_route`
directly against a temp SQLite file: create → list(filter) → invalid create(400) →
get-by-id → update → delete(204) → get(404) → health. Registered as a single ctest target.

# Architecture summary: book_api (C++17 / Boost.Beast + SQLite)

A single-header REST service (327 LOC total) implementing CRUD for a book collection.

## Modules
- **api.hpp** (198 LOC) — the whole service. Contains:
  - `Statement` — RAII wrapper over `sqlite3_stmt` (prepare/bind/step/column extraction, `book()` row→JSON).
  - `open_database()` — opens SQLite, creates `books` table (`id PK AUTOINCREMENT, title/author NOT NULL, year, isbn`).
  - `decode()` — URL percent/plus decoding for query params.
  - `route()` — the HTTP router: dispatches `/health`, `/books`, `/books/{id}` across GET/POST/PUT/DELETE; builds JSON `reply()` with correct status codes and `Allow`/`Location` headers.
  - `serve()` — reads one HTTP request off a socket, routes it, maps `BadInput`→400 and other exceptions→500, writes the response.
- **main.cpp** (20 LOC) — parses `[port] [database]`, opens DB, accepts TCP connections on loopback, calls `serve()` per socket.
- **test_transport.cpp** (12 LOC) — test shim: accepts a pre-connected socket fd + db path, calls `serve()` once. Lets the Python harness drive the real server over a `socketpair`.
- **tests.py** (74 LOC) — 4 integration tests (CRUD lifecycle, list+author-filter+persistence, validation matrix, health+routing) driving the compiled `test_transport` binary over sockets.
- **CMakeLists.txt** — Boost.json + SQLite3 + Threads; registers the Python-driven ctest.

## Request flow
socket → `http::read` → `route()` (path/method dispatch → prepared SQLite statement → JSON) → `http::write`. Validation (`title`/`author` nonblank strings, typed `year`/`isbn`) throws `BadInput`→400.

# Architecture Summary

> `run-summary` skill was not invoked separately (not registered in this session);
> this is a brief hand-written substitute.

Single-file C service (`book_service.c`, ~9.5 KB of dense one-line-per-function
source) built on **libmicrohttpd** for HTTP and **SQLite** for persistence.

## Modules / layers

- **Buffer helpers** (`Buf`, `append`, `adds`) — a growable byte buffer used to
  assemble JSON responses.
- **JSON helpers** (`jsonstr`, `books_json`) — manual JSON encoding; `books_json`
  serialises either a single book object or an array of books from a prepared
  statement.
- **Request parsing** (`field`, `url_decode`) — hand-rolled extraction of a key's
  value from a JSON request body and URL-decoding of query args.
- **DB helper** (`execute_book`) — binds up to five params and steps one statement
  (INSERT/UPDATE/DELETE).
- **HTTP router** (`handler`) — a flat `strcmp`/`strncmp` dispatch over
  `(method, url)`, covering `/health`, `/books`, `/books/{id}`, and CORS preflight.
- **`main`** — opens the DB (`BOOKS_DB` env or `books.db`), creates the `books`
  table, starts the daemon on port 8080 (or argv[1]).

## Request flow

`MHD` → `handler()` → route match → SQLite prepared statement →
`books_json`/manual body → `respond()` (sets `Content-Type: application/json`
and permissive CORS) → `MHD_queue_response`.

## Test harness

`test_api.c` `#define UNIT_TEST`s and `#include`s `book_service.c` to reach static
helpers, then asserts on `jsonstr`, `field`, and a direct SQLite CRUD + author
filter sequence. It never starts the daemon or drives a route through `handler()`.

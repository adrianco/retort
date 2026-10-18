# Architecture Summary — books-api (C + SQLite)

A single-binary REST service in C11. ~1355 lines of source + 315 lines of tests,
layered cleanly with each concern in its own translation unit and header.

## Modules

| Module | Role |
|--------|------|
| `main.c` | Entry point: parses `[port] [db-path]`, opens the DB, listens, serves. |
| `http.c/.h` | Minimal HTTP/1.1 server over POSIX sockets: `http_listen`, `http_port`, `http_serve`. Parses request line, headers, `Content-Length`, binds to 127.0.0.1. |
| `api.c/.h` | Routing + request/response layer. `api_handle` dispatches by method+path; builds JSON bodies and HTTP status codes; `api_error` for error envelopes. |
| `book.c/.h` | Domain + persistence. `Book` struct, JSON→Book validation (`book_from_json`), and SQLite CRUD (`db_open`, `book_insert/find/list/update/delete`) via prepared statements. |
| `json.c/.h` | Hand-written JSON object parser (strings, numbers, bools, null, nested skip) and `json_escape` for output. Handles `\uXXXX` incl. surrogate pairs. |
| `buf.c/.h` | Growable byte buffer (`buf_append`, `buf_printf`, `buf_puts`, `buf_steal`). |

## Request flow

`http_serve` reads a request → fills a `Request {method, path, query, body, body_len}`
→ `api_handle` routes:
- `/health` → GET returns `{"status":"ok"}`.
- `/books` → GET `list_books` (optional `?author=` via `query_param`+`url_decode`), POST `create_book`.
- `/books/{id}` → `parse_id` (positive decimal, ≤18 digits), then GET/PUT/DELETE.

Persistence is SQLite via parameterized prepared statements (no string interpolation →
no SQL injection). Schema auto-created on open with an index on `author`.

## Validation & status codes

- title/author required, non-blank, ≤255 bytes; year 0–9999 integer; isbn ISBN-10/13 format.
- Status codes: 201 create, 200 read/update, 204 delete, 400 bad input, 404 missing/unknown route, 405 method not allowed, 500 internal.

## Tests

`tests/test_api.c` — four suites driven through the real `api_handle` and a live socket:
`test_json` (parser edge cases), `test_validation` (8 rejection cases), `test_crud`
(full CRUD + filter + 404/405 paths), `test_http` (end-to-end over a background server thread).

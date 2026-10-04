# Architecture Summary: books_api (C++)

A dependency-free (beyond SQLite) REST service for a book collection, C++17.

## Modules

| File | Role |
|------|------|
| `src/store.{h,cpp}` | `BookStore` — SQLite persistence (CRUD, `?author=` filter), mutex-guarded, RAII `Stmt` wrapper, prepared/bound statements. |
| `src/api.{h,cpp}` | Transport-independent routing: `handle_request(store, Request) -> Response`. Payload parse/validation, id parse, status-code mapping, JSON serialization. |
| `src/http_server.{h,cpp}` | POSIX-socket HTTP/1.1 server; `parse_target` (path + query decode); dispatches to a handler callback. |
| `src/json.{h,cpp}` | Hand-rolled JSON parser + `quote()` serializer with unicode/escape handling. |
| `src/main.cpp` | Wires `BookStore` + `HttpServer`, reads `PORT`/`DB_PATH` env. |
| `tests/test_api.cpp` | 11 tests: handler-level (in-memory DB) + one end-to-end over a real socket. |

## Request flow

`socket -> HttpServer::serve -> parse_target -> handle_request (route) -> BookStore -> Response -> HTTP write`

The `api` layer is deliberately transport-independent, so tests exercise routing
directly against `:memory:` as well as through the real HTTP server.

## Notable design points

- SQLite parameter binding everywhere (no string interpolation); an injection
  attempt is asserted safe in `test_list_and_author_filter`.
- PUT is full-resource replacement (documented, tested).
- Errors funnel through a `try/catch` in `handle_request` → 500.

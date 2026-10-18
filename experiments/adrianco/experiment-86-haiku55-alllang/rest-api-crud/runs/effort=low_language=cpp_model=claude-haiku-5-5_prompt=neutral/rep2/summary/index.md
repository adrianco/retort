# Architecture Summary

C++17 REST service for a book collection, cleanly separated into a core library
(`book_core`) consumed by both the server executable and the test runner.

## Modules

| File | Responsibility |
|------|----------------|
| `src/database.{h,cpp}` | `BookRepository` — SQLite-backed, thread-safe CRUD. RAII `Statement` wrapper around prepared statements; schema (table + author index) created on open. `Book` / `BookFields` structs. `:memory:` supported for tests. |
| `src/validation.{h,cpp}` | `parse_book_fields` — validates a JSON body into `BookFields`; title/author required non-blank, year optional 0–9999, isbn optional. Accumulates *all* errors into a `ValidationError`. |
| `src/api.{h,cpp}` | `register_routes` — maps the six book routes + `/health` onto an `httplib::Server`; JSON (de)serialization, status codes, id parsing, exception handler. |
| `src/main.cpp` | Wires repository + server, binds `127.0.0.1` on `PORT` (default 8080), `DB_PATH` (default `books.db`). |
| `tests/test_books.cpp` | Self-contained test harness (no gtest); 11 cases across repository, validation, and HTTP integration layers (ephemeral in-memory server). |

## Request flow

`main` → `register_routes(server, repository)` → per-route lambda → `read_book_body`
(`json::parse` + `parse_book_fields`) → `BookRepository` method → `to_json` → `send_json`.
Errors flow through `send_error` (uniform `{"error", ["details"]}` JSON); a server-wide
`set_exception_handler` maps unexpected throws to 500.

## Dependencies

- cpp-httplib v0.18.7 (FetchContent) — HTTP server/client
- nlohmann/json v3.11.3 (FetchContent) — JSON
- system SQLite3 + Threads

## Notes

Layering is strict and testable: storage, validation and routing are independent and
each is unit-tested directly in addition to the end-to-end HTTP lifecycle test.

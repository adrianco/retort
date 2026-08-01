# Architecture Summary

A single-binary C++17 REST service (~242 LOC across 4 files) backed by SQLite.

## Modules

| File | Role |
|------|------|
| `book_service.hpp` | `BookService` class + `HttpResponse` struct. Declares the CRUD handlers and owns the raw `sqlite3*`. |
| `book_service.cpp` | All business logic: a hand-rolled JSON object parser, JSON escaping/serialization, request routing (`handle`), and the five CRUD handlers + `/health`. |
| `main.cpp` | A minimal blocking socket HTTP/1.1 server (POSIX sockets). Parses the request line + `Content-Length`, dispatches to `BookService::handle`, writes the response. |
| `tests.cpp` | Integration-style test driver: exercises the service through `handle()` end-to-end against a temp SQLite file. |

## Request flow

`main.cpp` accepts a socket → parses method/target/body → `BookService::handle(method, target, body)` routes on method+path → handler prepares a parameterized `sqlite3_stmt`, runs it, serializes rows via `book_json` → returns `{status, body}` → `main.cpp` writes the HTTP response with a status label and `Connection: close`.

## Notable design points

- **Persistence:** SQLite with `CREATE TABLE IF NOT EXISTS`; all queries use bound parameters (no SQL injection surface).
- **Routing:** `handle()` centralizes dispatch; `parse_id` validates `/books/{id}` is a positive integer.
- **Validation:** `title`/`author` required on create and update (400 otherwise); `year` must parse as int.
- **The service layer is transport-agnostic** — `handle()` takes plain strings, which is exactly why the tests can drive it without a socket.

# Codebase Summary — Objective-C Book Service

## Modules

| File | Role |
|------|------|
| `BookServer.h` | Public interface: `BookStore` (persistence) + `BookHTTPServer` (socket server + routing). |
| `BookServer.m` | Implementation of both classes. |
| `main.m` | CLI entry point: parses `--port`/`--db`, opens the store, starts the server, runs the run loop. |
| `Tests.m` | Integration test harness (plain `main`, custom `Check` assertions). |
| `Makefile` | `all` (book-service), `tests`, `test`, `clean`. clang + `-fobjc-arc`, `-framework Foundation`, `-lsqlite3`. |

## Interfaces

- **`BookStore`** — thin SQLite wrapper. `initWithPath:error:` creates a `books` table
  (`id` autoincrement, `title`/`author` NOT NULL, `year`, `isbn`). CRUD methods:
  `allBooksByAuthor:`, `bookWithID:`, `createBook:`, `updateBook:`, `deleteBook:`, plus
  `validBookFields:` (title+author non-blank). All queries use prepared statements with
  bound parameters (no SQL injection surface).
- **`BookHTTPServer`** — raw BSD-socket HTTP/1.1 server on `INADDR_LOOPBACK`, served on a
  serial dispatch queue. Reads the request honoring `Content-Length`, parses the JSON body,
  and dispatches by method+path.

## Request flow

Two parallel dispatchers share the store:
- `serveClient:` — the live path; writes the HTTP response to the socket.
- `responseForMethod:target:body:` — a pure function returning `{status, body}`, used by the
  tests. The two contain **duplicated routing logic**.

## Routes

`GET /health` → `{"status":"ok"}`; `GET /books` (+`?author=`); `POST /books` (201/400);
`GET|PUT|DELETE /books/{id}` (200/204/400/404); 405 for known paths with wrong method,
404 otherwise.

## Notes

- Persistence is real SQLite on disk (file path from `--db`, tests use a temp file).
- ARC enabled; sqlite statements finalized on every path including error `goto`s.

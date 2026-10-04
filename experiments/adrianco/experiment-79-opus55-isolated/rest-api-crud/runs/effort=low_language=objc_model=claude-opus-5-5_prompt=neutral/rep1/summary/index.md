# Architecture Summary — rest-api-crud (Objective-C, Opus 5.5, effort=low)

## Surface

A REST API for a book collection: CRUD over `/books`, an `?author=` filter, a
`/health` check, SQLite persistence, JSON responses with HTTP status codes, and
input validation (title/author required). Built with only macOS-native pieces —
Foundation, BSD sockets, and the system `libsqlite3` — with no third-party deps.

## Modules

| Module | Files | Responsibility |
|--------|-------|----------------|
| `BookStore` | `src/BookStore.{h,m}` | SQLite persistence. Thread-safe (`@synchronized`), prepared statements, one `books` table. CRUD + author filter (`COLLATE NOCASE`). |
| `BookAPI` | `src/BookAPI.{h,m}` | Transport-independent request handler: maps method + target + body → `APIResponse`. Routing, body validation, JSON encoding, status codes. |
| `HTTPServer` | `src/HTTPServer.{h,m}` | Minimal HTTP/1.1 server over BSD sockets (one request per connection). Header/body parsing, size limits, `100-continue`, dispatches to `BookAPI`. |
| `main` | `src/main.m` | Entry point: reads `DB_PATH`/`HOST`/`PORT` env, wires store→API→server, `dispatch_main()`. |
| tests | `tests/BookTests.m` | Self-contained runner (no XCTest): 10 test functions, API-level against `:memory:` DB + one end-to-end test over a real socket. |

## Interfaces

- `BookStore`: `initWithPath:error:`, `createBook:error:`, `listBooksWithAuthor:error:`,
  `bookWithID:error:`, `updateBook:fields:error:`, `deleteBook:found:error:`, `close`.
- `BookAPI`: `initWithStore:`, `handleMethod:target:body:` → `APIResponse` (status, body, headers).
- `HTTPServer`: `initWithAPI:`, `startOnHost:port:error:` (port 0 = ephemeral), `stop`.

## Control flow

`main` → `HTTPServer.startOnHost:port:` binds/listens, accept loop on a global queue,
each connection handled on a background queue → parse request → `BookAPI.handleMethod:target:body:`
→ route to `BookStore` → `APIResponse` serialized back over the socket with `Connection: close`.
The API layer is deliberately decoupled from transport, which is what lets the tests drive
it directly against an in-memory store as well as over HTTP.

## Notable choices

- PUT replaces the whole record (omitted optional fields become `null`).
- Author filter is exact, case-insensitive; values are bound, never interpolated (SQL-injection safe — tested).
- Validation rejects non-string title/author, blank-after-trim, non-integer/boolean `year`, non-string `isbn`.
- Body size capped at 1 MB (413); `Transfer-Encoding` rejected; headers capped at 64 KB.

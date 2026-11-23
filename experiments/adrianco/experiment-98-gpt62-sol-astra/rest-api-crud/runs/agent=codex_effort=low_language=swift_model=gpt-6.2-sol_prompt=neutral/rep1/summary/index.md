# Architecture summary — BookCollection (Swift)

A small, layered Swift Package Manager project implementing a book-collection REST API.

## Modules

| Target | File(s) | Role |
|--------|---------|------|
| `CSQLite` (system library) | `Sources/CSQLite/module.modulemap`, `shim.h` | Exposes the system `sqlite3` C library to Swift. |
| `BookAPI` (library) | `Sources/BookAPI/BookStore.swift` | Persistence layer: SQLite table DDL, prepared statements, CRUD + author-filtered list. Defines `BookInput` (with `isValid`) and `Book` models. |
| | `Sources/BookAPI/BookAPI.swift` | Routing/controller layer: parses method+target, dispatches to the store, builds `Response` objects with correct status codes. |
| | `Sources/BookAPI/HTTPServer.swift` | Transport layer: `Network`-framework `NWListener`, a line-oriented HTTP/1.1 parser (`HTTPConnection`) with header/body size limits, Content-Length handling, and a 15s connection timeout. |
| `BookServer` (executable) | `Sources/BookServer/main.swift` | Entry point: reads `PORT`/`BOOK_DB_PATH`, starts the server on port 8080. |
| `BookAPITests` (tests) | `Tests/BookAPITests/BookAPITests.swift` | 4 XCTest cases covering lifecycle, author filter + cross-connection persistence, validation/routing, and health. |

## Request flow

`HTTPConnection.process()` parses the request line and headers → `BookAPI.handle(method:target:body:)` validates the target, matches on `(method, path)` → `BookStore` executes a parameterized SQLite statement → `Response.json(...)` encodes the result → `HTTPConnection.send(...)` writes the HTTP response and closes the connection.

## Notable qualities

- Parameterized queries throughout (SQL-injection safe; a test asserts `?author=' OR 1=1` returns no rows).
- Clean separation of transport / routing / persistence; the test target drives the routing+store layer directly via an in-memory DB.
- Defensive HTTP parsing: rejects `Transfer-Encoding`, `Expect`, oversized headers/bodies, malformed Content-Length.

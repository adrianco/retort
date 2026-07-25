# Book Collection API

A small REST API for managing a collection of books, written in **Swift** with
**zero external dependencies**. It uses:

- **SQLite** (via the system `SQLite3` module) for persistent, embedded storage.
- Apple's **`Network` framework** for the HTTP/1.1 server.

Because there are no third-party packages, the project builds offline and has no
dependency-resolution step.

## Requirements

- macOS 12 or later
- Swift 5.9+ (`swift --version`)
- **Xcode** installed (the Command Line Tools alone do not ship `XCTest`, which
  is needed to run the test suite). Building and running the server works with
  either toolchain.

## Project layout

```
Sources/
  BookAPI/            Library: model, SQLite store, HTTP parser, router, server
    Book.swift          Book model + input validation
    BookStore.swift     Thread-safe SQLite-backed CRUD store
    HTTP.swift          HTTP request parser + response builder
    Router.swift        Routes requests to store operations (fully testable)
    HTTPServer.swift    TCP/HTTP server on the Network framework
  BookServer/         Executable entry point (main.swift)
Tests/
  BookAPITests/       Unit + integration tests
```

## Build

```bash
swift build
```

## Run

```bash
swift run BookServer
# or run the built binary directly:
./.build/debug/BookServer
```

The server listens on `http://127.0.0.1:8080` by default and stores data in
`books.db` in the working directory. Both are configurable via environment
variables:

```bash
PORT=9000 DB_PATH=/tmp/mybooks.db swift run BookServer
```

## Test

The test suite requires `XCTest`, which ships with Xcode. If your active
developer directory is the Command Line Tools, point at Xcode for this command:

```bash
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift test
```

If Xcode is already your selected toolchain (`xcode-select -p` shows a path
inside `Xcode.app`), plain `swift test` works.

The suite contains 20 tests across three files:
- `RouterTests.swift` — unit tests for every endpoint and validation rule.
- `HTTPParsingTests.swift` — unit tests for the HTTP request parser / response
  serializer.
- `IntegrationTests.swift` — boots the real server on an ephemeral port and
  drives a full create/read/update/delete lifecycle over live HTTP.

## API

All responses are JSON. A book is shaped like:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719" }
```

`year` and `isbn` are optional. `title` and `author` are **required** on create
and update.

| Method | Path            | Description                          | Success | Errors |
|--------|-----------------|--------------------------------------|---------|--------|
| GET    | `/health`       | Health check                         | 200     | —      |
| POST   | `/books`        | Create a book                        | 201     | 400 (validation) |
| GET    | `/books`        | List books (`?author=` filter)       | 200     | —      |
| GET    | `/books/{id}`   | Get a book by id                     | 200     | 404, 400 (bad id) |
| PUT    | `/books/{id}`   | Replace a book                       | 200     | 404, 400 |
| DELETE | `/books/{id}`   | Delete a book                        | 204     | 404    |

Validation errors and not-found responses return `{"error": "<message>"}` with
the appropriate status code.

### Examples

```bash
# Health
curl http://127.0.0.1:8080/health
# {"status":"ok"}

# Create
curl -X POST http://127.0.0.1:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'
# 201 {"author":"Frank Herbert","id":1,"isbn":"978-0441172719","title":"Dune","year":1965}

# List, filtered by author
curl "http://127.0.0.1:8080/books?author=Frank%20Herbert"

# Get one
curl http://127.0.0.1:8080/books/1

# Update
curl -X PUT http://127.0.0.1:8080/books/1 \
  -d '{"title":"Dune (Revised)","author":"Frank Herbert","year":1965}'

# Delete
curl -X DELETE http://127.0.0.1:8080/books/1   # 204 No Content

# Validation failure
curl -X POST http://127.0.0.1:8080/books -d '{"author":"No Title"}'
# 400 {"error":"title is required"}
```

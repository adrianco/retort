# Book collection API

A Swift HTTP service backed by SQLite. It uses Swift Package Manager and the system SQLite library; no third-party Swift packages are required.

## Setup and run

Install Swift 5.9 or later and SQLite development headers and library (on Debian/Ubuntu: `libsqlite3-dev`; macOS includes SQLite). From this directory:

```sh
swift build
swift run book-server
```

The server listens on port 8080 on all interfaces. Set `PORT` to change the port and `DATABASE_PATH` to change the SQLite file (default `books.sqlite` in the working directory). For example:

```sh
PORT=8081 DATABASE_PATH=/tmp/books.sqlite swift run book-server
```

Run tests with `swift test`.

## API

All responses are JSON. Book IDs are generated integers. `title` and `author` must be nonempty strings containing more than whitespace. `year` is an optional integer and `isbn` is an optional string; both may be omitted or null. PUT replaces all fields, so omitted optional fields are cleared. Author filtering is an exact, case-sensitive match.

- `GET /health` — health status.
- `POST /books` — create a book; returns 201 and the book.
- `GET /books` — list books, optionally filtered with `?author=...`.
- `GET /books/{id}` — retrieve a book.
- `PUT /books/{id}` — replace a book; returns the updated book.
- `DELETE /books/{id}` — delete a book; returns `{"deleted":true}`.

Malformed or invalid input returns 400, missing resources return 404, unsupported methods return 405, and database failures return 500. Errors have an `error` string field.

```sh
curl -X POST http://localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://localhost:8080/books?author=Frank%20Herbert'
curl http://localhost:8080/health
```

The built-in HTTP server handles one connection at a time, closes each connection after its response, and accepts request bodies up to 1 MiB with a Content-Length header. It is intended for simple deployments behind a production reverse proxy.

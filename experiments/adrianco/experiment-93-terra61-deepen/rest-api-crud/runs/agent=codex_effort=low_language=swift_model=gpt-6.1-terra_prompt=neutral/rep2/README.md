# Book collection API

A Swift REST service backed by SQLite. It uses Swift Package Manager and the system SQLite library; no third-party Swift packages are needed.

## Setup and run

Install Swift 5.9 or newer and SQLite development headers (on Debian/Ubuntu, `libsqlite3-dev`; on macOS, the Xcode command-line tools provide SQLite). From this directory:

```sh
swift build
swift run books-server
```

The server listens on all interfaces on port 8080 by default. Set `PORT` to change the port and `DATABASE_PATH` to change the database file (default: `books.sqlite` in the working directory). The database and table are created on startup.

```sh
PORT=3000 DATABASE_PATH=/tmp/books.sqlite swift run books-server
swift test
```

## API

All responses are JSON. Errors have an `error` string. Book IDs are positive integers. `title` and `author` must be non-empty strings after trimming whitespace. `year` (integer) and `isbn` (string) are optional and may be null. PUT replaces the complete book, so omitted optional fields become null. Author filtering is an exact, case-sensitive match.

- `GET /health` — service health, `200`.
- `POST /books` — create a book, `201`.
- `GET /books` — list books, optionally filter with `?author=...`, `200`.
- `GET /books/{id}` — retrieve a book, `200` or `404`.
- `PUT /books/{id}` — replace a book, `200` or `404`.
- `DELETE /books/{id}` — delete a book, `200` or `404`.

Invalid JSON or invalid book fields return `400`; unsupported methods return `405`. Example:

```sh
curl -X POST http://localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://localhost:8080/books?author=Frank%20Herbert'
curl http://localhost:8080/books/1
curl -X PUT http://localhost:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE http://localhost:8080/books/1
```

# BookAPI

A REST API for managing a book collection, written in Swift. Data is stored in
SQLite using the system `libsqlite3`. The HTTP layer uses Network.framework, so
the project has no third-party dependencies and runs on macOS 13+.

## Requirements

- macOS 13 or later
- Swift 5.9+ toolchain (Xcode 15 or later, or the `swift` CLI)

## Build, run, and test

```sh
swift build
swift test

# Run the server (defaults: PORT=8080, BOOKS_DB_PATH=./books.sqlite)
PORT=8080 BOOKS_DB_PATH=./books.sqlite swift run BookAPIServer
```

## API

| Method | Path          | Description                                   | Success |
|--------|---------------|-----------------------------------------------|---------|
| POST   | `/books`      | Create a book                                 | 201     |
| GET    | `/books`      | List books; `?author=` filters (case-insensitive exact match) | 200 |
| GET    | `/books/{id}` | Get one book                                  | 200     |
| PUT    | `/books/{id}` | Replace a book's fields                       | 200     |
| DELETE | `/books/{id}` | Delete a book                                 | 204     |
| GET    | `/health`     | Health check                                  | 200     |

A book has the shape `{"id": 1, "title": "...", "author": "...", "year": 1965, "isbn": "..."}`.
`year` and `isbn` are optional and may be `null`.

### Validation

- `title` and `author` are required and must not be blank (after trimming).
- `year`, if given, must be an integer from 1 to next calendar year.
- `isbn` is optional; blank values are stored as `null`.

Errors return `400` with `{"error": "..."}`. Unknown books return `404`, an
unsupported method on a known path returns `405` with an `Allow` header, and
malformed JSON returns `400`.

## Examples

```sh
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl "localhost:8080/books?author=Frank%20Herbert"
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

## Layout

- `Sources/BookAPI/Book.swift` — models and validation
- `Sources/BookAPI/BookStore.swift` — SQLite persistence
- `Sources/BookAPI/Router.swift` — maps requests to operations (no sockets; easy to test)
- `Sources/BookAPI/HTTPServer.swift` — HTTP/1.1 parsing and serving
- `Sources/BookAPIServer/main.swift` — executable entry point
- `Tests/BookAPITests` — unit and integration tests (in-memory SQLite, router-level)

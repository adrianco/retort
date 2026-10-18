# Book API

A REST API for managing a book collection, written in Swift with
[Hummingbird 2](https://github.com/hummingbird-project/hummingbird) and SQLite.

## Requirements

- Swift 6.x toolchain (developed with Swift 6.3 on macOS 26; macOS 14+ is the declared minimum)
- SQLite3 development library (ships with macOS; on Linux install `libsqlite3-dev`)

## Build and test

```sh
swift build
swift test
```

## Run

```sh
swift run BookAPIServer
```

Configuration is via environment variables:

| Variable        | Default          | Purpose                          |
|-----------------|------------------|----------------------------------|
| `DATABASE_PATH` | `books.sqlite3`  | SQLite file (created if missing) |
| `HOST`          | `127.0.0.1`      | Bind address                     |
| `PORT`          | `8080`           | Listen port                      |

## Endpoints

| Method | Path          | Description                                  | Success |
|--------|---------------|----------------------------------------------|---------|
| POST   | `/books`      | Create a book                                | 201     |
| GET    | `/books`      | List books; optional `?author=` (case-insensitive exact match) | 200 |
| GET    | `/books/{id}` | Get one book                                 | 200     |
| PUT    | `/books/{id}` | Replace a book's fields (full update)        | 200     |
| DELETE | `/books/{id}` | Delete a book                                | 204     |
| GET    | `/health`     | Health check, returns `{"status":"ok"}`      | 200     |

### Book fields

| Field    | Type    | Required | Rules                                                  |
|----------|---------|----------|--------------------------------------------------------|
| `title`  | string  | yes      | non-empty after trimming                               |
| `author` | string  | yes      | non-empty after trimming                               |
| `year`   | integer | yes      | 1000 through next calendar year                        |
| `isbn`   | string  | no       | ISBN-10 or ISBN-13 shape (hyphens/spaces allowed); check digit not verified |

### Examples

```sh
curl -X POST localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl "localhost:8080/books?author=frank%20herbert"
curl -X PUT localhost:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -X DELETE localhost:8080/books/1
```

### Errors

Errors return JSON `{"error": "..."}`. Validation failures (400) also include
`"details"` listing every problem found:

```json
{"error":"validation failed","details":["title is required","author is required"]}
```

| Status | Cause                                           |
|--------|-------------------------------------------------|
| 400    | Invalid JSON, validation failure, non-integer id |
| 404    | No book with that id                            |

## Layout

- `Sources/BookAPI/Book.swift` — models and validation
- `Sources/BookAPI/BookStore.swift` — SQLite storage (actor)
- `Sources/BookAPI/Routes.swift` — HTTP routes and application builder
- `Sources/BookAPIServer/main.swift` — executable entry point
- `Sources/CSQLite` — system library shim for `sqlite3`
- `Tests/BookAPITests` — HTTP integration tests and store/validator unit tests

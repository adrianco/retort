# Book API

A REST API service for managing a book collection, written in Swift using the
[Hummingbird 2](https://github.com/hummingbird-project/hummingbird) web
framework with SQLite storage (the system SQLite3 library — no extra database
dependency).

## Requirements

- Swift 6.0 or later (tested with Swift 6.3 on macOS)
- macOS 14+ (Hummingbird 2 requirement)

## Setup and run

```sh
swift build
swift run Server
```

The server listens on `127.0.0.1:8080` by default and stores data in
`books.sqlite` in the working directory. Configure via environment variables:

| Variable  | Default        | Description                    |
|-----------|----------------|--------------------------------|
| `HOST`    | `127.0.0.1`    | Address to bind                |
| `PORT`    | `8080`         | Port to bind                   |
| `DB_PATH` | `books.sqlite` | SQLite database file path      |

```sh
PORT=9000 DB_PATH=/tmp/books.sqlite swift run Server
```

## Running the tests

```sh
./test.sh
```

With a full Xcode install this is equivalent to `swift test`. On machines with
only the Command Line Tools, the script adds the search paths for the Swift
Testing framework that SwiftPM does not supply on its own.

The suite contains 7 integration tests covering every endpoint: health check,
create + fetch round-trip, input validation (missing/blank fields, malformed
JSON), listing with the author filter, update (including validation and 404),
delete (including repeat-delete 404), and unknown/malformed IDs.

## API

All request and response bodies are JSON.

| Method   | Path                  | Description                          | Success | Errors |
|----------|-----------------------|--------------------------------------|---------|--------|
| `GET`    | `/health`             | Health check (pings the database)    | 200     |        |
| `POST`   | `/books`              | Create a book                        | 201     | 400    |
| `GET`    | `/books`              | List books; `?author=` filters by author (case-insensitive exact match) | 200 | |
| `GET`    | `/books/{id}`         | Fetch a single book                  | 200     | 400, 404 |
| `PUT`    | `/books/{id}`         | Update a book (full replacement)     | 200     | 400, 404 |
| `DELETE` | `/books/{id}`         | Delete a book                        | 204     | 400, 404 |

### Book fields

| Field    | Type    | Notes                                  |
|----------|---------|----------------------------------------|
| `id`     | integer | Assigned by the server                 |
| `title`  | string  | **Required**, must be non-blank        |
| `author` | string  | **Required**, must be non-blank        |
| `year`   | integer | Optional                               |
| `isbn`   | string  | Optional                               |

Validation failures return `400` with a body like
`{"error":{"message":"'title' is required and must be a non-empty string"}}`.

### Examples

```sh
# Create
curl -X POST http://127.0.0.1:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Release It!","author":"Michael Nygard","year":2018,"isbn":"978-1680502398"}'
# -> 201 {"id":1,"title":"Release It!","author":"Michael Nygard","year":2018,"isbn":"978-1680502398"}

# List / filter
curl http://127.0.0.1:8080/books
curl 'http://127.0.0.1:8080/books?author=Michael%20Nygard'

# Fetch
curl http://127.0.0.1:8080/books/1

# Update (PUT is a full replacement; title and author are required)
curl -X PUT http://127.0.0.1:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Release It! 2nd Ed.","author":"Michael Nygard","year":2018}'

# Delete
curl -X DELETE http://127.0.0.1:8080/books/1   # -> 204

# Health
curl http://127.0.0.1:8080/health              # -> {"status":"ok"}
```

## Project layout

```
Sources/
  App/                      Library with all application logic (testable)
    Application+build.swift Router + application wiring
    BookController.swift    /books route handlers
    BookRepository.swift    SQLite-backed store (actor around one connection)
    Models.swift            Book, BookInput (validation), HealthResponse
  Server/
    Server.swift            Executable entry point; reads HOST/PORT/DB_PATH
Tests/
  AppTests/
    BookAPITests.swift      Integration tests via HummingbirdTesting (in-memory DB)
```

## Design notes

- **Storage** uses the system `SQLite3` C module directly, wrapped in an
  `actor` so the single connection is never touched by two threads at once.
  All statements are prepared with bound parameters (no SQL string
  interpolation).
- **Validation** decodes bodies into a struct with optional fields and then
  validates, so a missing `title`/`author` produces a clear 400 message rather
  than an opaque decoding error. Blank/whitespace-only values are rejected too.
- **Tests** run the real router against an in-memory SQLite database
  (`:memory:`), so they exercise routing, decoding, validation, status codes,
  and persistence without touching the filesystem or a real port.

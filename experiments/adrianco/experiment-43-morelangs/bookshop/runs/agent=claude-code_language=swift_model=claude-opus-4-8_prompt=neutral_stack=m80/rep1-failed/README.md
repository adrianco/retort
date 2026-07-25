# Book API

A small REST API for managing a book collection, built with **Swift** using the
[Vapor](https://vapor.codes) web framework, [Fluent](https://docs.vapor.codes/fluent/overview/)
ORM, and an embedded **SQLite** database.

## Requirements

- Swift 6.0+ toolchain (developed and tested with Swift 6.3)
- macOS 13+ or Linux

> **Note on running tests on macOS:** building only needs the Command Line Tools,
> but `swift test` requires the XCTest/Swift Testing runtime that ships with the
> full Xcode. If you have Xcode installed, prefix test commands with
> `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer` (see below).

## Setup

Resolve dependencies and build:

```bash
swift package resolve
swift build
```

## Running the server

```bash
swift run App serve --hostname 127.0.0.1 --port 8080
```

The server creates/uses a `db.sqlite` file in the working directory. It listens on
`http://127.0.0.1:8080` by default. A health check is available at `GET /health`.

## Running the tests

```bash
# macOS with full Xcode installed:
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift test

# Linux (or macOS where the default toolchain includes the test runtime):
swift test
```

The test suite (`Tests/AppTests/BookAPITests.swift`) runs against an in-memory
SQLite database and covers the health check, creation, validation, listing with the
author filter, single-book fetch/update/delete, and error responses (400/404).

## API

All request and response bodies are JSON.

| Method | Path            | Description                              | Success status |
|--------|-----------------|------------------------------------------|----------------|
| GET    | `/health`       | Health check                             | 200            |
| POST   | `/books`        | Create a book                            | 201            |
| GET    | `/books`        | List books (optional `?author=` filter)  | 200            |
| GET    | `/books/{id}`   | Get a single book by id                  | 200            |
| PUT    | `/books/{id}`   | Update a book                            | 200            |
| DELETE | `/books/{id}`   | Delete a book                            | 204            |

### Book fields

| Field    | Type    | Required | Notes                        |
|----------|---------|----------|------------------------------|
| `id`     | UUID    | —        | Server-generated             |
| `title`  | string  | yes      | Must be non-empty            |
| `author` | string  | yes      | Must be non-empty            |
| `year`   | integer | no       |                              |
| `isbn`   | string  | no       |                              |

### Validation & errors

- `title` and `author` are required and must be non-empty (whitespace is trimmed).
- Missing/empty required fields → `400 Bad Request`.
- A malformed id (not a UUID) → `400 Bad Request`.
- An unknown id → `404 Not Found`.

### Examples

```bash
# Health check
curl localhost:8080/health

# Create
curl -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# List all
curl localhost:8080/books

# List filtered by author
curl 'localhost:8080/books?author=Frank%20Herbert'

# Get one
curl localhost:8080/books/<id>

# Update
curl -X PUT localhost:8080/books/<id> \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

# Delete
curl -X DELETE localhost:8080/books/<id>
```

## Project layout

```
Sources/App/
  Models/Book.swift            # Fluent model
  Migrations/CreateBook.swift  # Schema migration
  DTOs/BookDTO.swift           # Request payload + validation
  Controllers/BookController.swift  # /books routes
  configure.swift              # DB + migrations wiring
  routes.swift                 # Route registration (incl. /health)
  entrypoint.swift             # @main
Tests/AppTests/
  BookAPITests.swift           # Integration tests
```

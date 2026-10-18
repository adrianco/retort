# BookAPI

A REST API for managing a book collection, written in Swift with
[Hummingbird 2](https://github.com/hummingbird-project/hummingbird) and stored in SQLite.

## Requirements

- Swift 5.10+ (tested with Swift 6.3 on macOS 26)
- SQLite development library. macOS ships it; on Debian/Ubuntu install `libsqlite3-dev`.

## Build and run

```sh
swift build
swift run BookAPI
```

The server listens on `http://127.0.0.1:8080` by default. Configure it with environment variables:

| Variable        | Default        | Purpose                          |
|-----------------|----------------|----------------------------------|
| `BOOKS_DB_PATH` | `books.sqlite` | SQLite database file (created if missing) |
| `HOST`          | `127.0.0.1`    | Interface to bind                |
| `PORT`          | `8080`         | Port to listen on                |

## Running tests

```sh
swift test
```

The suite covers input validation, the SQLite store, and HTTP integration tests for every endpoint.

## API

All request and response bodies are JSON.

A book has the shape:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719" }
```

`year` and `isbn` are optional and may be `null` or omitted.

| Method   | Path          | Description                                  | Success |
|----------|---------------|----------------------------------------------|---------|
| `POST`   | `/books`      | Create a book                                | `201` + book |
| `GET`    | `/books`      | List books; `?author=` filters by author (case-insensitive exact match) | `200` + array |
| `GET`    | `/books/{id}` | Get one book                                 | `200` + book |
| `PUT`    | `/books/{id}` | Replace a book's fields (full update)        | `200` + book |
| `DELETE` | `/books/{id}` | Delete a book                                | `204` (no body) |
| `GET`    | `/health`     | Health check, verifies the database responds | `200` `{"status":"ok"}` |

### Validation

- `title` and `author` are required and must not be blank.
- `year`, if given, must be between 0 and 9999.
- `isbn`, if given, must be a valid ISBN-10 (last character may be `X`) or ISBN-13. Hyphens and spaces are ignored.

### Errors

Errors return JSON `{"error": "..."}`. Validation failures also include `details`:

| Status | When |
|--------|------|
| `400`  | Invalid or missing fields, malformed JSON, non-integer `{id}` |
| `404`  | No book with that id |
| `503`  | Health check cannot reach the database |

## Examples

```sh
curl -X POST localhost:8080/books -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

curl 'localhost:8080/books?author=Frank%20Herbert'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

## Project layout

```
Sources/
  CSQLite/        System-library module wrapping sqlite3
  BookAPICore/    Models, validation, SQLite store, HTTP routes
  BookAPI/        Executable entry point
Tests/
  BookAPICoreTests/  Unit and HTTP integration tests
```

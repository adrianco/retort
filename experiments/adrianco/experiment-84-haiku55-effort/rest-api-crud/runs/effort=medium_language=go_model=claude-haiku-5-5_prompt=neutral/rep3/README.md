# Book Collection API

A small REST API for managing a book collection, written in Go with
`net/http` and SQLite. The SQLite driver is pure Go (`modernc.org/sqlite`), so
no C compiler or cgo is needed.

## Requirements

- Go 1.22 or newer (the code uses `ServeMux` method and path patterns; developed with Go 1.26)

## Setup

```sh
go mod download
```

## Run

```sh
go run .
```

The server listens on `:8080` and stores data in `books.db` in the current
directory. Both can be changed with environment variables:

| Variable  | Default    | Purpose                              |
|-----------|------------|--------------------------------------|
| `ADDR`    | `:8080`    | Address and port to listen on        |
| `DB_PATH` | `books.db` | Path to the SQLite database file     |

To build a binary instead:

```sh
go build -o bookapi .
./bookapi
```

## Test

```sh
go test ./...
```

The tests use an in-memory database and run the real router, so they cover
status codes, JSON bodies, validation, and a restart against a database file.

## Data model

| Field    | Type    | Required | Notes                                                        |
|----------|---------|----------|--------------------------------------------------------------|
| `id`     | integer | —        | Assigned by the server; read-only                            |
| `title`  | string  | yes      | Whitespace is trimmed; must not be blank                     |
| `author` | string  | yes      | Whitespace is trimmed; must not be blank                     |
| `year`   | integer | no       | `0` or omitted means unknown; otherwise 1 to next year       |
| `isbn`   | string  | no       | ISBN-10 or ISBN-13, hyphens and spaces allowed; checksum checked |

ISBNs are stored in normalized form (digits only, with a trailing `X` for an
ISBN-10 check digit). Each ISBN may belong to only one book. Books without an
ISBN are unrestricted.

## Endpoints

| Method   | Path          | Description                                  | Success |
|----------|---------------|----------------------------------------------|---------|
| `POST`   | `/books`      | Create a book                                | `201`   |
| `GET`    | `/books`      | List books; optional `?author=` filter       | `200`   |
| `GET`    | `/books/{id}` | Get one book                                 | `200`   |
| `PUT`    | `/books/{id}` | Replace a book's fields (full update)        | `200`   |
| `DELETE` | `/books/{id}` | Delete a book                                | `204`   |
| `GET`    | `/health`     | Liveness and database check                  | `200`   |

- `POST` and `PUT` take a JSON body with `title`, `author`, and optionally
  `year` and `isbn`. `PUT` replaces all fields, so omitting `isbn` clears it.
- `POST` responds with a `Location` header pointing at the new book.
- `?author=` matches case-insensitively and must equal the full author name.
  Results are ordered by `id`.
- `/health` returns `503` if the database cannot be reached.

### Examples

```sh
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"}'

# List by author
curl 'localhost:8080/books?author=Frank%20Herbert'

# Get, update, delete
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -i -X DELETE localhost:8080/books/1

# Health
curl localhost:8080/health
```

## Errors

Errors are JSON objects with an `error` field.

| Status | When                                                              |
|--------|-------------------------------------------------------------------|
| `400`  | Malformed JSON, invalid ID, or validation failure                 |
| `404`  | No book with that ID, or unknown route                            |
| `405`  | Method not supported on that path (response includes `Allow`)     |
| `409`  | Another book already has the same ISBN                            |
| `500`  | Unexpected server or database error (details are logged, not sent) |
| `503`  | `/health` cannot reach the database                               |

Validation failures list each problem by field:

```json
{
  "error": "validation failed",
  "fields": {
    "title": "title is required",
    "isbn": "isbn must be a valid ISBN-10 or ISBN-13"
  }
}
```

Request bodies are limited to 1 MiB.

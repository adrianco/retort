# Book Collection API (Go)

A small REST service for managing books. It uses Go's standard `net/http` router and stores data in SQLite through [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), a pure-Go driver, so it builds without cgo or a C compiler.

## Requirements

- Go 1.22 or newer (the router needs method and path-pattern routing)

## Setup and run

```sh
go mod download
go run .                     # listens on :8080 and uses ./books.db
```

Configuration comes from environment variables:

| Variable  | Default    | Description                     |
|-----------|------------|---------------------------------|
| `ADDR`    | `:8080`    | Address to listen on            |
| `DB_PATH` | `books.db` | SQLite file (created if absent) |

To build a binary instead: `go build -o bookapi . && ./bookapi`

## Tests

```sh
go test -v ./...
```

The tests exercise the full HTTP handler against a temporary SQLite database. They cover the health check, the create/read/update/delete lifecycle, the author filter, validation errors, 404 and 400 cases, persistence after reopening the database, and ISBN format checks.

## API

| Method | Path          | Description                    | Success |
|--------|---------------|--------------------------------|---------|
| GET    | `/health`     | Health check (pings the DB)    | 200     |
| POST   | `/books`      | Create a book                  | 201 (with a `Location` header) |
| GET    | `/books`      | List books; `?author=` filters | 200     |
| GET    | `/books/{id}` | Get one book                   | 200     |
| PUT    | `/books/{id}` | Replace a book                 | 200     |
| DELETE | `/books/{id}` | Delete a book                  | 204     |

Request body for POST and PUT:

```json
{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" }
```

### Validation rules

- `title` and `author` are required. Values that are empty or only whitespace are rejected.
- `year` is optional. If given, it must be between 0 and next year.
- `isbn` is optional. If given, it must have 10 or 13 digits. Hyphens and spaces are allowed, and an ISBN-10 may end in `X`.
- Unknown fields, malformed JSON and wrong types are rejected.

The `author` filter is an exact match that ignores case, for example `?author=jane%20austen`.

### Errors

Every error returns JSON with a matching status code: 400 for invalid input or ID, 404 when the book doesn't exist, 405 for an unsupported method, and 500 for internal errors. Validation errors also list the problem for each field:

```json
{ "error": "validation failed", "fields": { "title": "title is required" } }
```

### Example

```sh
curl -X POST localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Emma","author":"Jane Austen","year":1815}'
curl 'localhost:8080/books?author=Jane%20Austen'
curl -X PUT localhost:8080/books/1 -d '{"title":"Emma","author":"Jane Austen","year":1816}'
curl -X DELETE localhost:8080/books/1
```

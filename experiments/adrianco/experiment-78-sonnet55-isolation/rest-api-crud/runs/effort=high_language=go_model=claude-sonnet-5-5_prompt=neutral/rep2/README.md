# Book Collection API

A REST API for managing a book collection, written in Go using the standard
library `net/http` router and SQLite (via the pure-Go `modernc.org/sqlite`
driver, so no CGO or system SQLite is required).

## Requirements

- Go 1.22+ (uses method/path-pattern routing)

## Run

```sh
go run .                       # listens on :8080, stores data in ./books.db
go run . -addr :9000 -db /tmp/books.db
```

Configuration can also come from the `ADDR` and `DB_PATH` environment variables
(flags take precedence). Use `-db :memory:` for a throwaway database.

## Test

```sh
go test ./...
```

## Endpoints

| Method | Path            | Description                                   | Success |
|--------|-----------------|-----------------------------------------------|---------|
| GET    | `/health`       | Health check (verifies DB connectivity)       | 200     |
| POST   | `/books`        | Create a book                                 | 201     |
| GET    | `/books`        | List books; optional `?author=` filter        | 200     |
| GET    | `/books/{id}`   | Get one book                                  | 200     |
| PUT    | `/books/{id}`   | Replace a book's fields                       | 200     |
| DELETE | `/books/{id}`   | Delete a book                                 | 204     |

A book is `{"id": 1, "title": "...", "author": "...", "year": 1965, "isbn": "..."}`.

- `title` and `author` are required and must be non-blank; `year` (0–9999) and
  `isbn` are optional.
- The `author` filter is an exact, case-insensitive match.
- Errors are returned as `{"error": "message"}` with status 400 (invalid input
  or id), 404 (unknown id) or 500.

## Example

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:8080/books?author=Frank+Herbert'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

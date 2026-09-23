# Book Collection API (Go)

A REST API for managing a book collection, built with Go's standard `net/http`
router (Go 1.22+ method/path patterns) and SQLite via the pure-Go driver
`modernc.org/sqlite`, so you don't need CGO or a C toolchain.

## Requirements

- Go 1.22 or newer

## Setup and run

```sh
go mod download
go run .                               # listens on :8080, stores data in ./books.db
ADDR=:9000 DB_PATH=/tmp/books.db go run .   # override the defaults
```

Or build a binary with `go build -o bookapi . && ./bookapi`.

## Test

```sh
go test ./...
```

The tests cover health, the full CRUD lifecycle, author filtering, input
validation and error codes, ISBN checks, and persistence after reopening the
database. Each test uses its own temporary SQLite file.

## Endpoints

| Method | Path          | Description                          | Success |
|--------|---------------|--------------------------------------|---------|
| GET    | `/health`     | Health check (also pings the DB)     | 200     |
| POST   | `/books`      | Create a book                        | 201 (+ `Location` header) |
| GET    | `/books`      | List books; `?author=` filter        | 200     |
| GET    | `/books/{id}` | Get one book                         | 200     |
| PUT    | `/books/{id}` | Replace a book                       | 200     |
| DELETE | `/books/{id}` | Delete a book                        | 204     |

The `author` filter matches the whole name and ignores case.

### Book payload

```json
{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" }
```

- `title`, `author`: required, and must not be blank
- `year`: optional, from 0 to next year
- `isbn`: optional; 10 or 13 digits, with hyphens or spaces allowed (an ISBN-10 may end in `X`)

### Errors

All errors are JSON:

- `400`: malformed JSON, unknown fields, wrong types, or a non-numeric id → `{"error": "..."}`
- `422`: validation failed → `{"error": "validation failed", "fields": {"title": "title is required"}}`
- `404`: the book doesn't exist or the route is unknown
- `405`: the method isn't allowed on a known path
- `500`: internal error (details are logged, not returned)

### Example

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=frank%20herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:8080/books/1
```

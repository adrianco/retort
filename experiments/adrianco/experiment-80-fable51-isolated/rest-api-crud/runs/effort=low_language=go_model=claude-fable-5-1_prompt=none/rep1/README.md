# Books API

A REST API for managing a book collection, written in Go with the standard
library `net/http` router and SQLite (via the pure-Go `modernc.org/sqlite`
driver, so no cgo is needed).

## Setup and run

Requires Go 1.22+.

```bash
go mod download
go run .
```

Configuration (environment variables):

| Variable  | Default    | Description               |
|-----------|------------|---------------------------|
| `PORT`    | `8080`     | HTTP listen port          |
| `DB_PATH` | `books.db` | SQLite database file path |

## Endpoints

| Method | Path          | Description                              | Success |
|--------|---------------|------------------------------------------|---------|
| GET    | `/health`     | Health check                             | 200     |
| POST   | `/books`      | Create a book                            | 201     |
| GET    | `/books`      | List books (optional `?author=` filter)  | 200     |
| GET    | `/books/{id}` | Get one book                             | 200     |
| PUT    | `/books/{id}` | Replace a book                           | 200     |
| DELETE | `/books/{id}` | Delete a book                            | 204     |

Book fields: `title` (required), `author` (required), `year`, `isbn`.
Errors are returned as `{"error": "..."}` with 400 (invalid input or id),
404 (unknown book) or 500.

```bash
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:8080/books?author=Frank+Herbert'
```

## Tests

```bash
go test ./...
```

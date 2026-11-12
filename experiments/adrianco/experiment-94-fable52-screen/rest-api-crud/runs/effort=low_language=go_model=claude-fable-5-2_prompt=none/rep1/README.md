# Book Collection API

A small REST service for managing books, written in Go with the standard
library `net/http` router and SQLite (via the pure-Go `modernc.org/sqlite`
driver — no cgo or system SQLite needed).

## Setup

Requires Go 1.22 or newer.

```bash
go mod download
```

## Run

```bash
go run .
```

Configuration is via environment variables:

| Variable  | Default    | Purpose                   |
|-----------|------------|---------------------------|
| `PORT`    | `8080`     | Port to listen on         |
| `DB_PATH` | `books.db` | SQLite database file path |

## Test

```bash
go test ./...
```

Tests run against an in-memory SQLite database.

## API

| Method | Path          | Description                              | Success |
|--------|---------------|------------------------------------------|---------|
| GET    | `/health`     | Health check                             | 200     |
| POST   | `/books`      | Create a book                            | 201     |
| GET    | `/books`      | List books, optional `?author=` filter   | 200     |
| GET    | `/books/{id}` | Get one book                             | 200     |
| PUT    | `/books/{id}` | Replace a book                           | 200     |
| DELETE | `/books/{id}` | Delete a book                            | 204     |

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

`title` and `author` are required; `year` and `isbn` are optional. The
`author` filter is an exact, case-insensitive match. `PUT` replaces the whole
record, so omitted optional fields are reset.

Errors are JSON with an `error` message: `400` for invalid JSON, failed
validation (with a per-field `fields` object) or a malformed ID, and `404`
for an unknown book.

## Example

```bash
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:8080/books/1
```

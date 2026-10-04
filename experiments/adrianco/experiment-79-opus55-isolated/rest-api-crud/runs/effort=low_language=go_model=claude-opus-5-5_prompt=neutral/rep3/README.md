# Book Collection API

A small REST service for managing a book collection, written in Go with the
standard library `net/http` router and SQLite for storage
(`modernc.org/sqlite`, a pure-Go driver — no CGO or system SQLite needed).

## Requirements

- Go 1.22 or newer

## Setup and run

```bash
go mod download
go run .
```

The server listens on `:8080` and stores data in `books.db` in the current
directory. Both are configurable through environment variables:

| Variable  | Default    | Description                                   |
|-----------|------------|-----------------------------------------------|
| `ADDR`    | `:8080`    | Listen address                                |
| `DB_PATH` | `books.db` | SQLite database file (`:memory:` for no file) |

```bash
ADDR=:9000 DB_PATH=/tmp/books.db go run .
```

To build a binary: `go build -o books-api . && ./books-api`

## Tests

```bash
go test ./...
```

The tests exercise the HTTP handlers end to end against an in-memory SQLite
database.

## API

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

| Method | Path          | Description                          | Success |
|--------|---------------|--------------------------------------|---------|
| GET    | `/health`     | Health check                         | 200     |
| POST   | `/books`      | Create a book                        | 201     |
| GET    | `/books`      | List books; `?author=` filters       | 200     |
| GET    | `/books/{id}` | Get one book                         | 200     |
| PUT    | `/books/{id}` | Replace a book                       | 200     |
| DELETE | `/books/{id}` | Delete a book                        | 204     |

Notes:

- `title` and `author` are required and must not be blank. `year` and `isbn`
  are optional; `year` must be between 0 and 9999.
- `PUT` replaces the whole book, so omitted optional fields are reset.
- The `?author=` filter matches the full author name, case-insensitively.

Errors are JSON, e.g. `{"error": "book not found"}`:

| Status | Meaning                                           |
|--------|---------------------------------------------------|
| 400    | Malformed JSON, wrong field type, or invalid ID   |
| 404    | No book with that ID                              |
| 422    | Validation failed (includes a `fields` object)    |

```json
{"error": "validation failed", "fields": {"title": "title is required"}}
```

## Examples

```bash
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl localhost:8080/books
curl 'localhost:8080/books?author=Frank%20Herbert'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

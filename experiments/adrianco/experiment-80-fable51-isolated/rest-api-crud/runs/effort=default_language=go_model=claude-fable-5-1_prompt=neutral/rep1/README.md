# Book Collection API

A small REST service for managing a book collection, written in Go with the
standard library `net/http` router and SQLite for storage
([modernc.org/sqlite](https://pkg.go.dev/modernc.org/sqlite), a pure-Go driver,
so no C compiler is needed).

## Requirements

- Go 1.26 or newer (see `go.mod`); dependencies are fetched automatically on first build

## Run

```bash
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

To build a binary instead: `go build -o bookapi . && ./bookapi`

## Test

```bash
go test ./...
```

The tests drive the HTTP handler end to end against an in-memory SQLite database.

## API

All request and response bodies are JSON. A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

| Method | Path          | Description                          | Success | Errors   |
|--------|---------------|--------------------------------------|---------|----------|
| GET    | `/health`     | Health check                         | 200     | 503      |
| POST   | `/books`      | Create a book                        | 201     | 400      |
| GET    | `/books`      | List books; `?author=` filters       | 200     |          |
| GET    | `/books/{id}` | Get one book                         | 200     | 400, 404 |
| PUT    | `/books/{id}` | Replace a book                       | 200     | 400, 404 |
| DELETE | `/books/{id}` | Delete a book                        | 204     | 400, 404 |

Notes:

- `title` and `author` are required and must not be blank; `year` and `isbn`
  are optional (`year` must not be negative).
- `PUT` replaces the whole record, so omitted optional fields are reset.
- The `author` filter is a case-insensitive exact match.
- Errors are returned as `{"error": "..."}`; validation failures also include
  a `details` array listing each problem.

### Examples

```bash
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl localhost:8080/books
curl 'localhost:8080/books?author=Frank+Herbert'
curl localhost:8080/books/1

curl -X PUT localhost:8080/books/1 \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966,"isbn":"9780441013593"}'

curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

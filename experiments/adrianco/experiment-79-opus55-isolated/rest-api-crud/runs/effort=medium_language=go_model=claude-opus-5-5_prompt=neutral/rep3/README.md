# Books API

A REST API for managing a book collection, written in Go with the standard
library `net/http` router and SQLite for storage.

## Requirements

- Go 1.26 or later (the version declared in `go.mod`)

SQLite is provided by [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite),
a pure-Go driver, so no C compiler or system SQLite library is needed.

## Setup and run

```bash
go mod download
go run .
```

The server listens on `:8080` and stores data in `books.db` in the current
directory. Both are configurable through environment variables:

| Variable  | Default    | Description                                       |
|-----------|------------|---------------------------------------------------|
| `ADDR`    | `:8080`    | Listen address                                    |
| `DB_PATH` | `books.db` | SQLite database file (`:memory:` for non-durable) |

```bash
ADDR=:9000 DB_PATH=/tmp/books.db go run .
```

To build a binary instead:

```bash
go build -o books .
./books
```

## Tests

```bash
go test ./...
```

The tests exercise the HTTP handlers end to end against a real SQLite database
(in-memory, plus one on-disk test for persistence).

## API

A book has the following shape:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

| Method | Path          | Description                          | Success |
|--------|---------------|--------------------------------------|---------|
| GET    | `/health`     | Health check                         | 200     |
| POST   | `/books`      | Create a book                        | 201     |
| GET    | `/books`      | List books, optionally `?author=`    | 200     |
| GET    | `/books/{id}` | Get one book                         | 200     |
| PUT    | `/books/{id}` | Replace a book                       | 200     |
| DELETE | `/books/{id}` | Delete a book                        | 204     |

Behaviour notes:

- `title` and `author` are required and must not be blank. `year` and `isbn`
  are optional and default to `0` and `""`; `year` must not be negative.
- `PUT` replaces the whole book, so omitted optional fields are reset to their
  defaults.
- The `?author=` filter is an exact, case-insensitive match on the author name.
- Errors are returned as JSON: `{"error": "..."}`. Validation failures also
  include a per-field `details` object.

| Status | Meaning                                              |
|--------|------------------------------------------------------|
| 400    | Malformed JSON, failed validation, or invalid ID     |
| 404    | No book with that ID                                 |
| 405    | Method not supported on that path                    |
| 413    | Request body larger than 1 MB                        |

### Examples

```bash
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl localhost:8080/books
curl 'localhost:8080/books?author=Frank%20Herbert'
curl localhost:8080/books/1

curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'

curl -i -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

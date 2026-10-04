# Book Collection API

A REST API for managing a book collection, written in Go with the standard
library's `net/http` router and SQLite for storage.

The SQLite driver is [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite),
a pure-Go implementation, so no C compiler or cgo is needed.

## Requirements

- Go 1.26 or newer (the version declared in `go.mod`)

## Setup and run

```bash
go mod download
go run .
```

The server listens on `:8080` and stores data in `books.db` in the current
directory. Both are configurable through environment variables:

| Variable  | Default    | Description                                      |
|-----------|------------|--------------------------------------------------|
| `ADDR`    | `:8080`    | Address to listen on                             |
| `DB_PATH` | `books.db` | SQLite database file (`:memory:` for ephemeral)  |

```bash
ADDR=:9000 DB_PATH=/tmp/books.db go run .
```

To build a binary instead:

```bash
go build -o bookapi .
./bookapi
```

## Tests

```bash
go test ./...
```

The tests drive the HTTP handlers against an in-memory SQLite database, plus
one test that reopens an on-disk database to check persistence.

## API

A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

| Method | Path          | Description                          | Success | Errors        |
|--------|---------------|--------------------------------------|---------|---------------|
| GET    | `/health`     | Health check (pings the database)    | 200     | 503           |
| POST   | `/books`      | Create a book                        | 201     | 400, 413      |
| GET    | `/books`      | List books, optionally `?author=`    | 200     |               |
| GET    | `/books/{id}` | Get one book                         | 200     | 400, 404      |
| PUT    | `/books/{id}` | Replace a book                       | 200     | 400, 404, 413 |
| DELETE | `/books/{id}` | Delete a book                        | 204     | 400, 404      |

Behaviour worth knowing:

- `title` and `author` are required and must not be blank. `year` and `isbn`
  are optional and default to `0` and `""`; `year` must not be negative.
  Leading and trailing whitespace is trimmed from string fields.
- `PUT` replaces the whole record, so omitted optional fields are reset to
  their defaults.
- `?author=` matches the full author name, case-insensitively.
- `GET /books` returns books in ID order, and `[]` when there are none.
- A successful `POST` sets a `Location` header pointing at the new book.
- A non-numeric or non-positive `{id}` is a 400; an unknown one is a 404.

Errors are JSON. Validation failures list the offending fields:

```json
{"error": "validation failed", "details": {"title": "title is required"}}
```

### Examples

```bash
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl localhost:8080/books
curl 'localhost:8080/books?author=Frank+Herbert'
curl localhost:8080/books/1

curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966,"isbn":"9780441013593"}'

curl -i -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

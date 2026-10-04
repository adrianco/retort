# Book Collection API

A REST API for managing a book collection, written in Go using the standard
library `net/http` router and SQLite for storage (via the pure-Go
`modernc.org/sqlite` driver, so no C compiler is needed).

## Requirements

- Go 1.22 or newer

## Setup and run

```bash
go mod download
go run .
```

The server listens on `:8080` and stores data in `books.db` in the current
directory. Both are configurable through environment variables:

| Variable  | Default    | Description                                        |
|-----------|------------|----------------------------------------------------|
| `ADDR`    | `:8080`    | Address to listen on                               |
| `DB_PATH` | `books.db` | SQLite database file (`:memory:` for non-persistent) |

```bash
ADDR=:9000 DB_PATH=/tmp/books.db go run .
```

To build a binary instead: `go build -o bookapi . && ./bookapi`

## Tests

```bash
go test ./...
```

The tests exercise the HTTP handlers end to end against a real SQLite database
(in-memory, plus one on-disk persistence test).

## API

A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

`title` and `author` are required; `year` and `isbn` are optional (defaulting
to `0` and `""`). `year` must not be negative.

| Method | Path          | Description                                  | Success |
|--------|---------------|----------------------------------------------|---------|
| GET    | `/health`     | Health check                                 | 200     |
| POST   | `/books`      | Create a book                                | 201     |
| GET    | `/books`      | List books; `?author=` filters by author (exact, case-insensitive) | 200 |
| GET    | `/books/{id}` | Get one book                                 | 200     |
| PUT    | `/books/{id}` | Replace a book (full update, same body as POST) | 200  |
| DELETE | `/books/{id}` | Delete a book                                | 204     |

Error responses are JSON of the form `{"error": "..."}`:

| Status | When                                                        |
|--------|-------------------------------------------------------------|
| 400    | Malformed JSON body, or an ID that is not a positive integer |
| 404    | No book with that ID                                        |
| 422    | Validation failed; a `fields` object describes each problem |

### Examples

```bash
curl -i -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl localhost:8080/books
curl 'localhost:8080/books?author=Frank+Herbert'
curl localhost:8080/books/1

curl -X PUT localhost:8080/books/1 \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

curl -i -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

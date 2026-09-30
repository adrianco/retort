# Book Collection API

A REST API for managing a book collection, written in Go using the standard
library `net/http` router and SQLite (via the pure-Go `modernc.org/sqlite`
driver, so no CGO or system SQLite is needed).

## Requirements

- Go 1.22 or newer

## Run

```sh
go run .            # listens on :8080, stores data in ./books.db
```

Configuration via environment variables:

| Variable  | Default    | Description                                  |
|-----------|------------|----------------------------------------------|
| `ADDR`    | `:8080`    | Listen address                               |
| `DB_PATH` | `books.db` | SQLite file path (`:memory:` for ephemeral)  |

Build a binary with `go build -o bookapi .`.

## Test

```sh
go test ./...
```

## Endpoints

| Method | Path           | Description                                  | Success |
|--------|----------------|----------------------------------------------|---------|
| GET    | `/health`      | Health check                                 | 200     |
| POST   | `/books`       | Create a book                                | 201     |
| GET    | `/books`       | List books; optional `?author=` filter       | 200     |
| GET    | `/books/{id}`  | Get one book                                 | 200     |
| PUT    | `/books/{id}`  | Replace a book's fields                      | 200     |
| DELETE | `/books/{id}`  | Delete a book                                | 204     |

Book JSON: `{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}`

- `title` and `author` are required (whitespace-only is rejected).
- `year` is optional (0 = unknown), must be between 0 and next year.
- `isbn` is optional, at most 20 characters.
- The `?author=` filter is an exact, case-insensitive match.
- `PUT` is a full replacement, so it needs `title` and `author` too.

Errors are JSON: `{"error": "..."}`. Status codes: `400` malformed JSON, unknown
fields or invalid id; `404` book not found; `422` validation failure (with a
`fields` map); `413` body over 1 MiB; `500` internal error.

## Example

```sh
curl -i -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

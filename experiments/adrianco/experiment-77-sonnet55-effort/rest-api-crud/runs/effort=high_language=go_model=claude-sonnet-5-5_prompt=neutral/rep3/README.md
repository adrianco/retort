# Book Collection API

A REST API for managing a book collection, written in Go using the standard
library `net/http` router and SQLite (via the pure-Go `modernc.org/sqlite`
driver, so no C toolchain is needed).

## Setup and run

Requires Go 1.22 or newer.

```sh
go build -o bookapi .
./bookapi            # listens on :8080, stores data in ./books.db
```

Configuration via environment variables:

| Variable  | Default    | Description                |
|-----------|------------|----------------------------|
| `ADDR`    | `:8080`    | Address to listen on       |
| `DB_PATH` | `books.db` | Path to the SQLite database |

## Test

```sh
go test ./...
```

## Endpoints

| Method | Path           | Description                                | Success |
|--------|----------------|--------------------------------------------|---------|
| GET    | `/health`      | Health check                               | 200     |
| POST   | `/books`       | Create a book                              | 201     |
| GET    | `/books`       | List books; optional `?author=` exact match | 200     |
| GET    | `/books/{id}`  | Get one book                               | 200     |
| PUT    | `/books/{id}`  | Replace a book's fields                    | 200     |
| DELETE | `/books/{id}`  | Delete a book                              | 204     |

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

`title` and `author` are required (non-blank); `year` must not be negative;
`year` and `isbn` are optional. Unknown JSON fields are rejected.

Errors are returned as `{"error": "..."}` with status `400` (malformed JSON or
bad id), `404` (no such book) or `422` (validation failure).

## Example

```sh
curl -i -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:8080/books/1
```

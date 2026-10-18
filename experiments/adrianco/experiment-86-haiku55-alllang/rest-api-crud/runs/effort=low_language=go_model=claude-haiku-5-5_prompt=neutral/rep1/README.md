# Book Collection API

A REST API for managing a book collection, written in Go with the standard
library `net/http` router and SQLite storage. SQLite is provided by
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), a pure-Go driver,
so no C compiler or cgo is required.

## Requirements

- Go 1.22 or newer (uses method-aware `ServeMux` patterns and `PathValue`)

## Setup

```sh
go mod download
```

## Run

```sh
go run .
```

The server listens on `:8080` by default. Configure with environment variables:

| Variable   | Default     | Description                              |
|------------|-------------|------------------------------------------|
| `ADDR`     | `:8080`     | Address to listen on                     |
| `BOOKS_DB` | `books.db`  | SQLite file path (`:memory:` for in-memory) |

Example:

```sh
ADDR=:9000 BOOKS_DB=./data/books.db go run .
```

## Test

```sh
go test ./...
```

## Data model

| Field    | Type    | Required | Notes                                  |
|----------|---------|----------|----------------------------------------|
| `id`     | integer | —        | Assigned by the server                 |
| `title`  | string  | yes      | Must not be blank                      |
| `author` | string  | yes      | Must not be blank                      |
| `year`   | integer | no       | 0 to next calendar year; defaults to 0 |
| `isbn`   | string  | no       | Free text, defaults to empty           |

## Endpoints

| Method   | Path          | Success | Description                              |
|----------|---------------|---------|------------------------------------------|
| `GET`    | `/health`     | 200     | Liveness and database connectivity check |
| `POST`   | `/books`      | 201     | Create a book                            |
| `GET`    | `/books`      | 200     | List books; optional `?author=` filter (exact match) |
| `GET`    | `/books/{id}` | 200     | Get one book                             |
| `PUT`    | `/books/{id}` | 200     | Replace a book's fields                  |
| `DELETE` | `/books/{id}` | 204     | Delete a book                            |

Request bodies are JSON. Unknown fields are rejected. Bodies are limited to 1 MiB.

### Examples

```sh
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# List, filtered by author
curl 'localhost:8080/books?author=Frank%20Herbert'

# Get
curl localhost:8080/books/1

# Update
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# Delete
curl -i -X DELETE localhost:8080/books/1

# Health
curl localhost:8080/health
```

## Error responses

All errors are JSON with an `error` field:

- `400` — invalid ID, malformed JSON, unknown field, or validation failure.
  Validation failures also include a `fields` object mapping field names to messages.
- `404` — book not found, or unknown route.
- `500` — unexpected internal error.
- `503` — `/health` only, when the database is unreachable.

```json
{"error":"validation failed","fields":{"title":"title is required"}}
```

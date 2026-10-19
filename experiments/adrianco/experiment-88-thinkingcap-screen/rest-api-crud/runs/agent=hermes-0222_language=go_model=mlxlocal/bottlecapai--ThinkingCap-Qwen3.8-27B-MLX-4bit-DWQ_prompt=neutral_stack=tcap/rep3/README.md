# Book API

A REST API service for managing a book collection, written in Go (Gin) with
SQLite storage (pure-Go driver, no CGO required).

## Endpoints

| Method | Path          | Description                                    |
|--------|---------------|------------------------------------------------|
| GET    | `/health`     | Health check (also verifies DB connectivity)   |
| POST   | `/books`      | Create a book                                  |
| GET    | `/books`      | List books (optional `?author=` filter)        |
| GET    | `/books/{id}` | Get a book by ID                               |
| PUT    | `/books/{id}` | Update a book                                  |
| DELETE | `/books/{id}` | Delete a book                                  |

## Book shape

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441172719"
}
```

- `title` and `author` are **required** (non-empty) on create and update.
- `year` (integer 0–9999) and `isbn` (string) are optional. `year: 0` and an
  empty `isbn` mean "not specified".
- On `PUT`, omitting `year`/`isbn` keeps the stored values; including them
  overwrites them.

## Status codes

- `200` — success (GET, PUT, health)
- `201` — created (POST), body is the new book with its ID
- `204` — deleted (DELETE), empty body
- `400` — validation error or malformed ID/body, body is `{"error": "..."}`
- `404` — book not found
- `500` — internal error
- `503` — health check failed (database unreachable)

## Setup

Requires Go 1.22+ (tested with Go 1.26). No CGO or system SQLite needed.

```sh
go mod tidy   # fetch dependencies (gin, modernc.org/sqlite)
```

## Run

```sh
go run .                 # listens on :8000, data in ./books.db
go run . -addr :9000     # custom port
go run . -db /tmp/x.db   # custom database file
```

Build a binary:

```sh
go build -o bookapi .
./bookapi
```

## Example session

```sh
curl -s localhost:8000/health
# {"status":"ok"}

curl -s -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'
# {"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}

curl -s 'localhost:8000/books?author=Frank%20Herbert'
curl -s localhost:8000/books/1
curl -s -X PUT localhost:8000/books/1 \
  -H 'Content-Type: application/json' -d '{"title":"Dune","author":"Frank Herbert"}'
curl -s -X DELETE localhost:8000/books/1 -w '%{http_code}'
# 204
```

## Tests

Unit tests (store) and integration tests (HTTP handlers) live in
`internal/store` and `internal/api`. Run them with:

```sh
go test ./...
```

## Project layout

```
main.go               entry point (flags, graceful shutdown)
internal/store/       SQLite persistence layer + unit tests
internal/api/         Gin HTTP handlers + integration tests
```

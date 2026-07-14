# Book Collection REST API

A small REST service for managing a collection of books, written in Go with a pure-Go SQLite backend (`modernc.org/sqlite`) and the standard library's `net/http` router.

## Requirements

- Go 1.22+ (uses the `net/http` method-prefix routing introduced in 1.22)

## Setup and run

```sh
go mod download
go build ./...
./bookapi
```

Environment variables:

- `ADDR` — listen address (default `:8080`)
- `DB_DSN` — SQLite DSN/path (default `books.db`; use `:memory:` for an in-memory DB)

## Endpoints

| Method | Path           | Description                                 |
| ------ | -------------- | ------------------------------------------- |
| GET    | `/health`      | Health check (verifies DB connectivity)     |
| POST   | `/books`       | Create a book (`title`, `author` required)  |
| GET    | `/books`       | List all books. Optional `?author=` filter  |
| GET    | `/books/{id}`  | Get a single book                           |
| PUT    | `/books/{id}`  | Replace a book                              |
| DELETE | `/books/{id}`  | Delete a book                               |

### Book JSON

```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Donovan",
  "year": 2015,
  "isbn": "978-0134190440"
}
```

### Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — invalid JSON or missing required field
- `404 Not Found` — unknown book id
- `503 Service Unavailable` — health check failed

## Example

```sh
curl -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Book","author":"Me","year":2024,"isbn":"123"}'

curl localhost:8080/books
curl 'localhost:8080/books?author=Me'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Book2","author":"Me","year":2025,"isbn":"123"}'
curl -X DELETE localhost:8080/books/1
```

## Tests

```sh
go test ./...
```

Integration tests use an in-memory SQLite database and exercise the HTTP handlers through `httptest`.

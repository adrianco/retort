# Book Collection API

A small REST API for storing books in SQLite. It uses Go's standard `net/http` server and the embedded `modernc.org/sqlite` driver.

## Requirements

- Go 1.23 or later

## Run

```sh
go mod tidy
go run .
```

The service listens on `:8080` and creates `books.db` in the current directory. Set `ADDR` to change the listen address or `BOOKS_DB` to change the SQLite file path.

## API

- `POST /books` — create a book with JSON fields `title`, `author`, `year`, and `isbn` (title and author are required).
- `GET /books` — list books; optionally pass `?author=Frank%20Herbert` for an exact author filter.
- `GET /books/{id}` — retrieve a book.
- `PUT /books/{id}` — replace a book's fields.
- `DELETE /books/{id}` — delete a book (returns 204 on success).
- `GET /health` — check service and database availability.

Responses use JSON. Missing records return 404, malformed or invalid input returns 400, and unsupported methods return 405.

Example:

```sh
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl http://localhost:8080/books
```

## Verify

```sh
go test ./...
go build ./...
```

# Book Collection API

A REST API for managing a book collection. It uses Go's `net/http` package and SQLite, with the pure-Go `modernc.org/sqlite` driver.

## Requirements

- Go 1.23 or newer

## Run

```sh
go mod tidy
go run .
```

The service listens on `:8080` and stores its database in `books.db` in the current directory by default. Set `ADDR` to change the listen address or `BOOKS_DB` to change the database path.

## API

- `POST /books` — create a book. JSON fields: `title`, `author`, `year`, `isbn`. Title and author are required.
- `GET /books` — list books; optionally filter with `?author=Name`.
- `GET /books/{id}` — fetch a book.
- `PUT /books/{id}` — replace a book's fields.
- `DELETE /books/{id}` — delete a book (returns `204 No Content`).
- `GET /health` — health check.

Successful responses use JSON, except delete. Invalid input receives `400`, unknown book IDs receive `404`, and unsupported methods receive `405`.

## Test

```sh
go test ./...
```

Example:

```sh
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```

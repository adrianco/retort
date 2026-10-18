# Book Collection API

A small REST API for managing books, implemented in Go with SQLite.

## Requirements

- Go 1.24 or newer

## Run

```sh
go run .
```

The server listens on `:8080` and creates `books.db` in the current directory. Set `ADDR` to change the listen address, or `DATABASE_PATH` to select another SQLite database path.

## Endpoints

- `GET /health` — readiness check
- `POST /books` — create a book with `title`, `author`, `year`, and `isbn`
- `GET /books` — list books; optionally filter with `?author=Name`
- `GET /books/{id}` — retrieve one book
- `PUT /books/{id}` — replace a book's fields
- `DELETE /books/{id}` — delete a book

Title and author are required. Book requests and responses use JSON. Errors return a JSON object containing an `error` field.

Example:

```sh
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

## Test

```sh
go test ./...
```

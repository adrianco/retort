# Book Collection API

A small REST API for managing books, backed by an embedded SQLite database.
The SQLite driver is pure Go, so no system SQLite library is required.

## Requirements

- Go 1.24 or newer

## Run

```sh
go run .
```

The service listens on `:8080` and creates `books.db` in the current directory.
Set `ADDR` to change the listen address or `BOOKS_DB` to change the database
path (for example, `BOOKS_DB=/tmp/books.db`).

## Endpoints

- `GET /health` — health status
- `POST /books` — create a book with `title`, `author`, optional `year`, and
  optional `isbn`
- `GET /books` — list books; `?author=Name` filters by exact author
- `GET /books/{id}` — retrieve one book
- `PUT /books/{id}` — replace a book's fields
- `DELETE /books/{id}` — delete a book

Example create request:

```sh
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

Titles and authors are required. Invalid JSON or missing required fields return
`400`; missing book IDs return `404`; successful creation returns `201`, and
successful deletion returns `204`.

## Tests

```sh
go test ./...
```

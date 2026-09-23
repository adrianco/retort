# Book Collection API

A small REST API for managing books, backed by SQLite.

## Requirements

- Go 1.23 or newer
- A C compiler for the SQLite driver (`github.com/mattn/go-sqlite3`)

## Run

```sh
go mod tidy
go run .
```

The service listens on `:8080` by default and creates `books.db` in the current directory. Set `ADDR` to change the listen address or `BOOKS_DB` to choose a different SQLite database file.

## Endpoints

- `GET /health` — health status
- `POST /books` — create a book; JSON fields: `title`, `author`, `year`, `isbn`
- `GET /books` — list books; optionally filter with `?author=Name`
- `GET /books/{id}` — fetch one book
- `PUT /books/{id}` — replace a book's fields
- `DELETE /books/{id}` — remove a book (returns `204 No Content`)

Titles and authors are required. Errors return a JSON object with an `error` field.

Example:

```sh
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```

## Test

```sh
go test ./...
```

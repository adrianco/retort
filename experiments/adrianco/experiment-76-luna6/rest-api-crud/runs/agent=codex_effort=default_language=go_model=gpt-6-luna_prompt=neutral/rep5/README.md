# Books REST API

A small Go REST API for a SQLite-backed book collection. It uses Go's standard
`net/http` server and the pure-Go `modernc.org/sqlite` SQLite driver.

## Requirements

- Go 1.25 or newer

## Run

```sh
go mod download
go run .
```

The service listens on `http://localhost:8080` and creates `books.db` in the
current directory. Set `DB_PATH` to choose another SQLite database path, or use
`:memory:` for a temporary in-memory database.

## Endpoints

- `GET /health` — service health
- `POST /books` — create a book; JSON fields: `title`, `author`, `year`, `isbn`
- `GET /books` — list books, optionally filtered with `?author=...`
- `GET /books/{id}` — retrieve one book
- `PUT /books/{id}` — replace a book's fields
- `DELETE /books/{id}` — remove a book

Title and author must be non-empty. Successful creation returns `201`; reads
and updates return `200`; deletes return `204`. Invalid requests return `400`,
missing books return `404`, and unsupported methods return `405`. Responses with
a body are JSON.

Example:

```sh
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://localhost:8080/books?author=Frank%20Herbert'
```

## Tests

```sh
go test ./...
```

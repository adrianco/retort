# Book Collection API

A small REST API for creating, listing, updating, and deleting books. It uses Go's `net/http` server and SQLite for persistent storage.

## Requirements

- Go 1.22 or newer

## Run

```sh
go run .
```

The service listens on `:8080` and creates `books.db` in the current directory. Set `ADDR` to change the listen address or `DB_PATH` to choose another SQLite database file.

## Endpoints

- `GET /health` — database health status
- `POST /books` — create a book with JSON fields `title`, `author`, `year`, and `isbn`
- `GET /books` — list books; optionally filter with `?author=...`
- `GET /books/{id}` — retrieve a book
- `PUT /books/{id}` — replace a book's fields
- `DELETE /books/{id}` — delete a book

Title and author are required. API responses use JSON; a successful delete returns `204 No Content`.

Example:

```sh
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```

## Test

```sh
go test ./...
```

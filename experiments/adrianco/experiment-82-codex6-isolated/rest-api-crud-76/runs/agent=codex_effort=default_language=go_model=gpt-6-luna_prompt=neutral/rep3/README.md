# Book Collection API

A small REST API written in Go. It stores books in an embedded SQLite database and serves JSON over HTTP.

## Requirements

- Go 1.26 or newer

## Run

```sh
go mod download
go run .
```

The server listens on `:8080` and creates `books.db` in the current directory. Set `ADDR` to change the listen address or `BOOKS_DB` to change the SQLite database path.

## Endpoints

- `GET /health` — health status
- `POST /books` — create a book with `title`, `author`, and optional `year` and `isbn`
- `GET /books` — list books; add `?author=Name` to filter by exact author
- `GET /books/{id}` — fetch one book
- `PUT /books/{id}` — replace a book's editable fields
- `DELETE /books/{id}` — delete a book

Titles and authors are required. Invalid input returns `400`, missing books return `404`, creation returns `201`, successful reads and updates return `200`, and successful deletion returns `204`.

Example:

```sh
curl -X POST http://localhost:8080/books \\
  -H 'Content-Type: application/json' \\
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```

## Tests

```sh
go test ./...
```

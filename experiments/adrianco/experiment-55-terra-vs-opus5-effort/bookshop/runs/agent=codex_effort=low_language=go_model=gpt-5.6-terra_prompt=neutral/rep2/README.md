# Book Collection API

A Go REST API for storing books in a SQLite database.

## Run

Requires Go and a C compiler (the SQLite driver uses CGO).

```sh
go mod download
go run .
```

The service listens on `http://localhost:8080`. Set `ADDR` to change the listen address and `BOOKS_DB` to change the SQLite database path (default: `books.db`).

## Endpoints

- `GET /health`
- `POST /books` — JSON body: `title`, `author`, optional `year`, `isbn`
- `GET /books` — optional exact-match filter: `?author=...`
- `GET /books/{id}`
- `PUT /books/{id}` — same JSON body as POST
- `DELETE /books/{id}`

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

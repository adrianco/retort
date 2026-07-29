# Book API

A small REST API for managing books, built with Go's `net/http` and SQLite.

## Run

```sh
go run .
```

The server listens on port `8080`. Set `PORT` to use another port and
`DATABASE_PATH` to choose the SQLite database file.

## Endpoints

- `GET /health`
- `POST /books` with JSON fields `title`, `author`, `year`, and `isbn`
- `GET /books` (optionally `?author=...`)
- `GET /books/{id}`
- `PUT /books/{id}` with JSON book fields
- `DELETE /books/{id}`

Example:

```sh
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

Run tests with `go test ./...`.

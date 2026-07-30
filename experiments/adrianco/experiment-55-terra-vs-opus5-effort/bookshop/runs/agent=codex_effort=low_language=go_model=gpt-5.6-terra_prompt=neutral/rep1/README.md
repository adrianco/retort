# Book Collection API

A Go REST API backed by SQLite for creating, listing, retrieving, updating, and deleting books.

## Run

Requires Go 1.26+ and a C compiler (the SQLite driver uses CGO).

```sh
go mod download
go run .
```

The service listens on `http://localhost:8080` and creates `books.db` in the working directory. Set `DATABASE_URL` to use another SQLite database path and `ADDR` to change the listen address.

## Endpoints

- `GET /health`
- `POST /books` — JSON body: `title`, `author`, optional `year`, `isbn`
- `GET /books` — use `?author=Name` to filter
- `GET /books/{id}`
- `PUT /books/{id}` — same JSON body as POST
- `DELETE /books/{id}`

Example:

```sh
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```

All successful non-empty responses are JSON. Missing or blank `title` and `author` return `400` with a JSON error. A missing book returns `404`.

## Test

```sh
go test ./...
```

# Books API

A small REST service for managing a book collection, written in Go using only the
standard library `net/http` router (Go 1.22+ method/path patterns) and SQLite via the
pure-Go `modernc.org/sqlite` driver (no cgo required).

## Requirements

- Go 1.22 or newer

## Setup and run

```sh
go mod download
go run .
```

The server listens on `:8080` and stores data in `books.db` in the working directory.

Environment variables:

| Variable   | Default    | Description                                  |
|------------|------------|----------------------------------------------|
| `ADDR`     | `:8080`    | Listen address                               |
| `BOOKS_DB` | `books.db` | SQLite file path (`:memory:` for in-memory)  |

Build a binary:

```sh
go build -o books-api .
./books-api
```

## Run the tests

```sh
go test ./...
```

## API

All responses are JSON. Errors look like `{"error": "message"}`.

| Method | Path                    | Description                                   | Success |
|--------|-------------------------|-----------------------------------------------|---------|
| GET    | `/health`               | Health check (`{"status":"ok"}`)              | 200     |
| POST   | `/books`                | Create a book                                 | 201     |
| GET    | `/books`                | List books; optional `?author=` exact filter  | 200     |
| GET    | `/books/{id}`           | Get one book                                  | 200     |
| PUT    | `/books/{id}`           | Replace a book                                | 200     |
| DELETE | `/books/{id}`           | Delete a book                                 | 204     |

Status codes: `400` for invalid JSON, invalid ID, or failed validation
(`title` and `author` are required, `year` must be 0–9999), `404` when the book
does not exist, `500` on database errors.

### Book body

```json
{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

### Examples

```sh
curl -X POST localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl localhost:8080/books
curl 'localhost:8080/books?author=Frank%20Herbert'
curl localhost:8080/books/1

curl -X PUT localhost:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

curl -X DELETE localhost:8080/books/1 -i
```

## Layout

- `main.go` — configuration and server startup
- `handlers.go` — HTTP routes, JSON encoding, validation errors
- `store.go` — SQLite schema and data access
- `main_test.go` — integration tests against an in-memory database

# Book Collection API

A small REST service in Go for managing a book collection, backed by SQLite
(`modernc.org/sqlite`, pure Go, no cgo). Routing uses the standard library
`net/http` mux (Go 1.22+ method/path patterns).

## Requirements

- Go 1.22 or newer

## Run

```sh
go mod tidy
go run .
```

The server listens on `:8080` and stores data in `books.db` in the working
directory. Override with environment variables:

| Variable   | Default    | Purpose                      |
|------------|------------|------------------------------|
| `ADDR`     | `:8080`    | Listen address               |
| `BOOKS_DB` | `books.db` | SQLite file path (DSN)       |

## Test

```sh
go test ./...
```

## Endpoints

| Method | Path                    | Description                              |
|--------|-------------------------|------------------------------------------|
| GET    | `/health`               | Health check, returns `{"status":"ok"}`  |
| POST   | `/books`                | Create a book (201)                      |
| GET    | `/books`                | List books; optional `?author=` filter   |
| GET    | `/books/{id}`           | Get one book (404 if missing)            |
| PUT    | `/books/{id}`           | Replace a book (200 / 404)               |
| DELETE | `/books/{id}`           | Delete a book (204 / 404)                |

Book JSON shape:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

`title` and `author` are required; missing or blank values return 400 with
`{"error": "..."}`. Unknown fields and malformed JSON are also rejected with 400.

### Examples

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:8080/books/1
```

# Books API

A REST API service for managing a book collection, written in Go using the
standard library `net/http` router (Go 1.22+) and SQLite for storage via the
pure-Go [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) driver
(no cgo required).

## Requirements

- Go 1.22 or later

## Setup & Run

```sh
go mod download   # fetch dependencies
go run .          # starts on :8080, creates books.db in the working dir
```

Environment variables:

| Variable   | Default    | Description                  |
|------------|------------|------------------------------|
| `ADDR`     | `:8080`    | Listen address               |
| `BOOKS_DB` | `books.db` | Path to the SQLite database  |

## Run tests

```sh
go test ./...
```

## API

| Method | Path          | Description                                  |
|--------|---------------|----------------------------------------------|
| GET    | `/health`     | Health check, returns `{"status":"ok"}`      |
| POST   | `/books`      | Create a book → `201` with the created book  |
| GET    | `/books`      | List books; supports `?author=` exact filter |
| GET    | `/books/{id}` | Get one book → `200`, or `404` if missing    |
| PUT    | `/books/{id}` | Update a book → `200`, or `404` if missing   |
| DELETE | `/books/{id}` | Delete a book → `204`, or `404` if missing   |

A book looks like:

```json
{"id": 1, "title": "The Mythical Man-Month", "author": "Fred Brooks", "year": 1975, "isbn": "978-0201835953"}
```

Validation: `title` and `author` are required (non-blank); `year` must not be
negative. Invalid input returns `400` with `{"error": "<message>"}`.

## Examples

```sh
# Create
curl -s -X POST localhost:8080/books \
  -d '{"title":"The Mythical Man-Month","author":"Fred Brooks","year":1975,"isbn":"978-0201835953"}'

# List (optionally filtered by author)
curl -s 'localhost:8080/books?author=Fred%20Brooks'

# Get / Update / Delete
curl -s localhost:8080/books/1
curl -s -X PUT localhost:8080/books/1 -d '{"title":"MMM (anniversary ed.)","author":"Fred Brooks","year":1995}'
curl -s -X DELETE localhost:8080/books/1 -w '%{http_code}\n'
```

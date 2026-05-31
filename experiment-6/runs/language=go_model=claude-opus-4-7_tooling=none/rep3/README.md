# bookapi

A small REST API for managing a book collection. Written in Go using only the
standard library `net/http` and the pure-Go SQLite driver
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) (no CGO required).

## Requirements

- Go 1.26 or newer

## Setup

```sh
go mod download
```

## Run

```sh
go run .
```

The server listens on `:8080` by default and stores data in `books.db` in the
working directory. Override via environment variables:

| Variable    | Default     | Purpose                        |
|-------------|-------------|--------------------------------|
| `BOOKS_ADDR` | `:8080`    | Address the HTTP server binds to |
| `BOOKS_DB`   | `books.db` | Path to the SQLite database file |

Example:

```sh
BOOKS_ADDR=:9000 BOOKS_DB=/tmp/books.db go run .
```

## Test

```sh
go test ./...
```

## API

All request and response bodies are JSON. A book is represented as:

```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Donovan & Kernighan",
  "year": 2015,
  "isbn": "978-0134190440"
}
```

`title` and `author` are required on `POST` and `PUT`; `year` and `isbn` are
optional.

### Endpoints

| Method | Path           | Description                                    |
|--------|----------------|------------------------------------------------|
| GET    | `/health`      | Health check. Returns `{"status":"ok"}` on 200. |
| POST   | `/books`       | Create a book. Returns the created book (201). |
| GET    | `/books`       | List books. Supports `?author=<name>` filter.  |
| GET    | `/books/{id}`  | Fetch a book by ID.                            |
| PUT    | `/books/{id}`  | Replace a book by ID.                          |
| DELETE | `/books/{id}`  | Delete a book by ID (204 on success).          |

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — malformed JSON, validation failure, or invalid ID
- `404 Not Found` — book ID does not exist
- `405 Method Not Allowed` — unsupported method on a known path
- `503 Service Unavailable` — `/health` when the DB is unreachable

### Examples

```sh
# Create
curl -s -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Donovan & Kernighan","year":2015,"isbn":"978-0134190440"}'

# List all
curl -s http://localhost:8080/books

# Filter by author
curl -s 'http://localhost:8080/books?author=Donovan%20%26%20Kernighan'

# Get one
curl -s http://localhost:8080/books/1

# Update
curl -s -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"TGPL","author":"Donovan & Kernighan","year":2015,"isbn":"978-0134190440"}'

# Delete
curl -s -X DELETE http://localhost:8080/books/1 -o /dev/null -w '%{http_code}\n'
```

## Layout

```
main.go           server bootstrap
store.go          SQLite-backed storage
handlers.go       HTTP handlers and routing
handlers_test.go  integration tests using an in-memory SQLite DB
```

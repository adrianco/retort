# Book API

A small REST service in Go for managing a book collection, backed by SQLite.

## Requirements

- Go 1.22 or newer (uses the `http.ServeMux` method-pattern routing)

The SQLite driver is `modernc.org/sqlite` (pure Go), so **no CGO toolchain is needed**.

## Setup

```sh
go mod tidy
go build ./...
```

## Run

```sh
go run .
```

Environment variables:

| Variable     | Default     | Purpose                       |
|--------------|-------------|-------------------------------|
| `BOOKS_DB`   | `books.db`  | SQLite database file path     |
| `BOOKS_ADDR` | `:8080`     | Listen address                |

The server creates the `books` table on startup if it does not exist.

## Endpoints

All endpoints accept and return JSON.

| Method | Path           | Description                                  |
|--------|----------------|----------------------------------------------|
| GET    | `/health`      | Liveness probe — returns `{"status":"ok"}`   |
| POST   | `/books`       | Create a book                                |
| GET    | `/books`       | List books, optional `?author=` filter       |
| GET    | `/books/{id}`  | Get a single book                            |
| PUT    | `/books/{id}`  | Replace a book                               |
| DELETE | `/books/{id}`  | Delete a book                                |

### Book payload

```json
{
  "title":  "The Go Programming Language",
  "author": "Donovan & Kernighan",
  "year":   2015,
  "isbn":   "978-0134190440"
}
```

`title` and `author` are required (non-empty after trimming whitespace).
`year` and `isbn` are optional.

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — invalid JSON or missing required field
- `404 Not Found` — unknown book id
- `500 Internal Server Error` — database failure

## Examples

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

# Health
curl -s http://localhost:8080/health
```

## Tests

```sh
go test ./...
```

The test suite (`handlers_test.go`) covers:

1. `TestHealth` — health endpoint returns `ok`
2. `TestCreateAndGetBook` — POST then GET round-trip
3. `TestCreateValidationMissingFields` — `400` when `title` or `author` is missing
4. `TestListWithAuthorFilter` — `?author=` filter returns the matching subset
5. `TestUpdateAndDelete` — PUT / DELETE happy paths plus 404s for unknown ids

Each test uses a fresh SQLite database in a per-test temp directory, so they are isolated and safe to run in parallel.

## Project layout

```
main.go             # entry point — wires store + server, starts http.ListenAndServe
store.go            # SQLite-backed Store: schema + CRUD
handlers.go         # HTTP handlers and routes
handlers_test.go    # integration tests against an in-process server
go.mod / go.sum     # module definition and locked dependencies
```

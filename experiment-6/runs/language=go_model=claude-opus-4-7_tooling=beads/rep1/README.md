# Books API

A small REST API in Go for managing a book collection. Persists to a SQLite file via the pure-Go `modernc.org/sqlite` driver (no CGO required).

## Requirements

- Go 1.21+ (developed against Go 1.26)

## Setup

```sh
go mod download
go build ./...
```

## Run

```sh
go run .
```

The server listens on `:8080` and writes to `books.db` in the working directory by default. Override with environment variables:

| Variable     | Default     | Description                  |
|--------------|-------------|------------------------------|
| `BOOKS_ADDR` | `:8080`     | Address to listen on         |
| `BOOKS_DB`   | `books.db`  | SQLite database file path    |

## Endpoints

| Method | Path           | Description                              |
|--------|----------------|------------------------------------------|
| GET    | `/health`      | Liveness check, returns `{"status":"ok"}`|
| POST   | `/books`       | Create a book                            |
| GET    | `/books`       | List books, optional `?author=` filter   |
| GET    | `/books/{id}`  | Fetch a book by ID                       |
| PUT    | `/books/{id}`  | Replace a book                           |
| DELETE | `/books/{id}`  | Delete a book                            |

### Book schema

```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Donovan",
  "year": 2015,
  "isbn": "9780134190440"
}
```

`title` and `author` are required for `POST` and `PUT`; `year` and `isbn` are optional.

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation failure or malformed JSON
- `404 Not Found` — unknown book ID
- `405 Method Not Allowed` — unsupported method on a known path

### Example

```sh
# Create
curl -s -X POST localhost:8080/books \
  -H 'content-type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Donovan","year":2015,"isbn":"9780134190440"}'

# List, filter by author
curl -s 'localhost:8080/books?author=Donovan'

# Fetch one
curl -s localhost:8080/books/1

# Update
curl -s -X PUT localhost:8080/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Donovan & Kernighan","year":2015,"isbn":"9780134190440"}'

# Delete
curl -i -X DELETE localhost:8080/books/1

# Health
curl -s localhost:8080/health
```

## Tests

```sh
go test ./...
```

The suite covers health, create + read, validation (missing/blank title, missing author, malformed JSON), list with `?author=` filter, update (including 404), delete (including 404 on second delete), 404 on missing fetch, and 405 on unsupported method. Tests use an in-memory SQLite database, no fixtures required.

## Project layout

- `main.go` — entrypoint: opens SQLite, builds server, listens
- `book.go` — `Book` model and `Store` (migrations + CRUD against SQLite)
- `handlers.go` — `Server` with `net/http` mux and request handlers
- `handlers_test.go` — integration tests against the full HTTP surface

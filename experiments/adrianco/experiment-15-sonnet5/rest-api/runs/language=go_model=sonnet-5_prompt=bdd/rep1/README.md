# Book Collection API

A REST API for managing a book collection, written in Go using the standard
library's `net/http` and a SQLite database (via the pure-Go `modernc.org/sqlite`
driver, so no CGO or system SQLite library is required).

## Requirements

- Go 1.22 or later

## Setup

```bash
go mod download
```

## Run

```bash
go run .
```

The server listens on `:8080` by default and stores data in `books.db`
(created automatically in the working directory on first run).

Environment variables:

- `BOOKS_ADDR` — address to listen on (default `:8080`)
- `BOOKS_DB_PATH` — path to the SQLite database file (default `books.db`)

## API

### Health check

```
GET /health
```

Returns `200 OK` with `{"status": "ok"}`.

### Create a book

```
POST /books
Content-Type: application/json

{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}
```

`title` and `author` are required. Returns `201 Created` with the created
book (including its assigned `id`), or `400 Bad Request` if validation fails.

### List books

```
GET /books
GET /books?author=Frank+Herbert
```

Returns `200 OK` with a JSON array of books, optionally filtered by an exact
`author` match.

### Get a book

```
GET /books/{id}
```

Returns `200 OK` with the book, or `404 Not Found` if it doesn't exist.

### Update a book

```
PUT /books/{id}
Content-Type: application/json

{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": "978-0441172696"}
```

Returns `200 OK` with the updated book, `400 Bad Request` if validation
fails, or `404 Not Found` if the book doesn't exist.

### Delete a book

```
DELETE /books/{id}
```

Returns `204 No Content` on success, or `404 Not Found` if the book doesn't
exist.

## Testing

```bash
go test ./...
```

Tests are written in a BDD (Given/When/Then) style, exercising the HTTP
handlers end-to-end against an in-memory SQLite database.

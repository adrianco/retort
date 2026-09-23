# Book Collection API

A REST API for managing a book collection, written in Go and backed by SQLite.

- HTTP routing uses the Go standard library (`net/http` method and path patterns), so no web framework is needed.
- Storage uses [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), a pure-Go SQLite driver. It needs no CGO and no C compiler.

## Requirements

- Go 1.25 or newer

## Setup and run

```sh
go mod download          # fetch dependencies
go build -o bookapi .    # build the binary
./bookapi                # listens on :8080, stores data in ./books.db
```

Or run it without building a binary:

```sh
go run .
```

### Configuration

| Flag    | Environment variable | Default    | Description                                        |
|---------|----------------------|------------|----------------------------------------------------|
| `-addr` | `PORT` (port only)   | `:8080`    | Address to listen on                               |
| `-db`   | `DB_PATH`            | `books.db` | SQLite database file, or `:memory:` for no persistence |

Examples:

```sh
PORT=3000 DB_PATH=/var/lib/books/books.db ./bookapi
./bookapi -addr 127.0.0.1:9000 -db :memory:
```

The database file and schema are created automatically on first start. The server shuts down cleanly on `SIGINT` or `SIGTERM`, and each request is logged to stderr.

## Running the tests

```sh
go test ./...
go test -race -cover ./...   # with the race detector and coverage
```

The tests cover:

- **`book_test.go`**: input validation rules, as table-driven unit tests.
- **`store_test.go`**: the SQLite store. This includes CRUD, not-found cases, the author filter (with LIKE wildcards escaped), IDs never being reused, and data surviving a reopen of the database file.
- **`handlers_test.go`**: integration tests that send real HTTP requests to the full router, backed by a real SQLite database. They cover the whole create/read/update/delete cycle, status codes, `Location` headers, validation and malformed-JSON errors, invalid IDs, 404/405/413/500/503 responses, the health check, and concurrent writes to a file-backed database.

## API

All responses are JSON (`Content-Type: application/json`), except `204 No Content`.

### Book resource

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "978-0-261-10221-7"
}
```

| Field    | Type           | Rules                                                                          |
|----------|----------------|--------------------------------------------------------------------------------|
| `id`     | integer        | Assigned by the server. Read-only, and never reused after a delete.            |
| `title`  | string         | **Required.** Leading and trailing whitespace is trimmed. Max 500 characters.  |
| `author` | string         | **Required.** Leading and trailing whitespace is trimmed. Max 200 characters.  |
| `year`   | integer / null | Optional. Must be between 1 and next year.                                     |
| `isbn`   | string / null  | Optional. Must be 10 or 13 digits once hyphens and spaces are removed. An ISBN-10 may end in `X`. Stored as given. An empty string is treated as null. |

The ISBN check verifies the format only. Check digits are not validated.

### Endpoints

| Method   | Path          | Description                          | Success           |
|----------|---------------|--------------------------------------|-------------------|
| `GET`    | `/health`     | Health check (also pings the database) | `200 OK`        |
| `POST`   | `/books`      | Create a book                        | `201 Created`, with a `Location` header |
| `GET`    | `/books`      | List all books, ordered by ID        | `200 OK`          |
| `GET`    | `/books/{id}` | Get one book                         | `200 OK`          |
| `PUT`    | `/books/{id}` | Replace a book                       | `200 OK`          |
| `DELETE` | `/books/{id}` | Delete a book                        | `204 No Content`  |

#### Filtering by author

`GET /books?author=<text>` returns only the books whose author **contains** `<text>`. The match is case-insensitive for ASCII letters, so `?author=tolkien` matches `J.R.R. Tolkien`. The `%` and `_` characters are matched literally. An empty `author` parameter returns every book. When nothing matches, the response is an empty array (`[]`).

#### PUT semantics

`PUT` replaces the whole book, so the same validation as `POST` applies and `title` and `author` are required. Any optional field that is left out (`year`, `isbn`) is cleared to `null`.

### Errors

Every error response has an `error` message. Validation failures also include a `fields` object that maps each invalid field to its problem:

```json
{"error": "validation failed", "fields": {"title": "is required", "author": "is required"}}
```

| Status | When                                                                                      |
|--------|-------------------------------------------------------------------------------------------|
| `400`  | Validation failed, the JSON is malformed or has the wrong types, the body is empty, or `{id}` is not a positive integer |
| `404`  | No book has that ID                                                                       |
| `405`  | The HTTP method is not supported on that path                                             |
| `413`  | The request body is larger than 1 MiB                                                     |
| `500`  | Unexpected server or database error. Details are logged but not returned to the client.  |
| `503`  | `GET /health` could not reach the database                                               |

### Example session

```sh
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0-261-10221-7"}'
# HTTP/1.1 201 Created
# Location: /books/1
# {"id":1,"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0-261-10221-7"}

# List, and filter by author
curl localhost:8080/books
curl 'localhost:8080/books?author=tolkien'

# Get one
curl localhost:8080/books/1

# Replace
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit, or There and Back Again","author":"J.R.R. Tolkien","year":1937}'

# Delete
curl -i -X DELETE localhost:8080/books/1     # 204 No Content

# Validation error
curl -X POST localhost:8080/books -d '{"year":1937}'
# {"error":"validation failed","fields":{"author":"is required","title":"is required"}}

# Health
curl localhost:8080/health                   # {"status":"ok"}
```

## Project layout

| File          | Contents                                                              |
|---------------|-----------------------------------------------------------------------|
| `main.go`     | Entry point: configuration, HTTP server setup, graceful shutdown       |
| `handlers.go` | Routes, request decoding, JSON responses, error mapping, request logging |
| `book.go`     | The `Book` model and input validation                                  |
| `store.go`    | The SQLite-backed store and its schema                                  |
| `*_test.go`   | Unit and integration tests                                             |

## Design notes

- **One database connection.** SQLite allows only one writer at a time. The store uses a single shared connection, with WAL journaling and a busy timeout. This avoids `SQLITE_BUSY` errors under concurrent requests. It is also what makes `:memory:` databases work, because each new connection to `:memory:` would otherwise open its own empty database. This setup suits a single-instance service. Scaling out would mean moving to a client-server database.
- **Atomic writes.** Inserts and updates use `RETURNING`, so each write and the read of its result happen in a single statement.
- **Duplicate ISBNs are allowed.** A collection can hold more than one copy or edition entry for the same ISBN.

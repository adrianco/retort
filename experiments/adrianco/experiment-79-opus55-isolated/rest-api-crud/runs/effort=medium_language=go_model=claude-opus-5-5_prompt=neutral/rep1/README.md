# Book Collection API

A small REST service for managing a book collection, written in Go with the
standard library's `net/http` router and SQLite for storage.

## Requirements

- Go 1.22 or newer (developed with Go 1.26)

The SQLite driver is [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite),
a pure-Go implementation, so no C compiler or system SQLite library is needed.

## Setup and run

```bash
go mod download      # fetch dependencies
go run .             # start the server on :8080, storing data in ./books.db
```

Or build a binary:

```bash
go build -o bookapi .
./bookapi
```

Configuration is through environment variables:

| Variable  | Default    | Description                                             |
|-----------|------------|---------------------------------------------------------|
| `PORT`    | `8080`     | TCP port to listen on                                   |
| `DB_PATH` | `books.db` | SQLite database file (`:memory:` for a non-persistent database) |

```bash
PORT=9000 DB_PATH=/tmp/books.db go run .
```

The database file and schema are created on first start. The server shuts down
gracefully on `SIGINT`/`SIGTERM`.

## Tests

```bash
go test ./...
```

The tests drive the HTTP handler end to end against an in-memory SQLite
database, so they need no setup and leave nothing behind.

## API

All request and response bodies are JSON.

A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

| Method   | Path          | Description               | Success          |
|----------|---------------|---------------------------|------------------|
| `GET`    | `/health`     | Health check              | `200 OK`         |
| `POST`   | `/books`      | Create a book             | `201 Created`    |
| `GET`    | `/books`      | List books                | `200 OK`         |
| `GET`    | `/books/{id}` | Get one book              | `200 OK`         |
| `PUT`    | `/books/{id}` | Replace a book            | `200 OK`         |
| `DELETE` | `/books/{id}` | Delete a book             | `204 No Content` |

### Behaviour

- **Validation** — `title` and `author` are required and must not be blank.
  `year` and `isbn` are optional; `year`, if given, must be between 0 and 9999.
  Leading and trailing whitespace is trimmed from string fields.
- **Filtering** — `GET /books?author=Frank+Herbert` returns only books by that
  author. The match is on the whole name and ignores case.
- **Updates** — `PUT` replaces the whole book, so it takes the same body as
  `POST` and applies the same validation. Omitted optional fields are reset
  to their defaults (`0` / `""`).
- **IDs** are assigned by the server; an `id` in a request body is ignored.

### Errors

Errors are returned as JSON with an `error` message. Validation failures also
list the offending fields:

```json
{"error": "validation failed", "fields": {"title": "title is required"}}
```

| Status | When                                                                 |
|--------|----------------------------------------------------------------------|
| `400`  | Malformed JSON, wrong field type, failed validation, non-numeric ID  |
| `404`  | No book with that ID, or unknown path                                |
| `405`  | Method not supported on that path                                    |
| `413`  | Request body larger than 1 MiB                                       |
| `500`  | Unexpected database error                                            |

### Examples

```bash
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# List, optionally filtered by author
curl localhost:8080/books
curl 'localhost:8080/books?author=Frank+Herbert'

# Get one
curl localhost:8080/books/1

# Update
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966,"isbn":"9780441013593"}'

# Delete
curl -i -X DELETE localhost:8080/books/1

# Health
curl localhost:8080/health
```

## Layout

| File               | Contents                                          |
|--------------------|---------------------------------------------------|
| `main.go`          | Configuration, server start-up, graceful shutdown |
| `handlers.go`      | Routing, request validation, JSON responses       |
| `store.go`         | SQLite schema and queries                         |
| `handlers_test.go` | Integration tests                                 |

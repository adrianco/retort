# Book Collection API

A small REST API for managing a collection of books, written in Go. It uses only
the standard library's `net/http` router and stores its data in an embedded
SQLite database (through a pure-Go driver, so no C compiler or system SQLite is
needed).

- Create, list, read, update and delete books, with an optional `?author=` filter
- JSON in, JSON out, with meaningful HTTP status codes
- Input validation: `title` and `author` are required
- `GET /health` endpoint that checks the database is reachable
- Graceful shutdown, request logging and panic recovery

## Requirements

- **Go 1.26 or newer.** Older toolchains from Go 1.21 onwards download the
  required version automatically.
- Network access the first time you build or test, to download the Go modules
  (`go mod download` fetches them up front).

## Setup and run

```sh
go run .
```

The server listens on port 8080 and creates the database file `books.db` in the
current directory on first start. Check that it is up:

```sh
curl -i localhost:8080/health
```

To build a binary instead:

```sh
go build -o bookapi .
./bookapi -addr :9000 -db /var/lib/books/books.db
```

Stop the server with Ctrl-C (or `SIGTERM`). It finishes in-flight requests
(up to 10 seconds) and closes the database cleanly.

### Configuration

| Flag    | Environment variable | Default    | Meaning                                                        |
|---------|----------------------|------------|----------------------------------------------------------------|
| `-addr` | `PORT` (port only)   | `:8080`    | Address to listen on, e.g. `:8080` or `127.0.0.1:9000`         |
| `-db`   | `DB_PATH`            | `books.db` | SQLite database file; `:memory:` gives a throwaway database    |

Flags take precedence over environment variables, for example
`PORT=9000 DB_PATH=/tmp/books.db go run .`. Run with `-h` to list the flags.

## API

| Method   | Path           | Description                                | Success           |
|----------|----------------|--------------------------------------------|-------------------|
| `POST`   | `/books`       | Create a book                              | `201 Created`     |
| `GET`    | `/books`       | List books (optionally `?author=`)         | `200 OK`          |
| `GET`    | `/books/{id}`  | Get one book                               | `200 OK`          |
| `PUT`    | `/books/{id}`  | Replace a book                             | `200 OK`          |
| `DELETE` | `/books/{id}`  | Delete a book                              | `204 No Content`  |
| `GET`    | `/health`      | Health check                               | `200 OK`          |

All responses except `204` are JSON (`Content-Type: application/json`).

### The book object

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" }
```

| Field    | Type    | Rules                                                                      |
|----------|---------|----------------------------------------------------------------------------|
| `id`     | integer | Assigned by the server and never reused. Ignored in request bodies.        |
| `title`  | string  | **Required**, at most 255 characters. Surrounding whitespace is trimmed.   |
| `author` | string  | **Required**, at most 255 characters. Surrounding whitespace is trimmed.   |
| `year`   | integer | Optional, 0 to 9999. `0` (or omitted) means "not provided".                |
| `isbn`   | string  | Optional, at most 32 characters. Free-form: the format is not validated.   |

### Endpoint behaviour

- **`POST /books`** returns `201` with the stored book and a `Location: /books/{id}` header.
- **`GET /books`** returns an array ordered by `id` (`[]` when there are no books).
  `?author=` keeps only books by that author: an exact match on the whole name,
  case-insensitive for ASCII letters, so `?author=jane austen` finds "Jane Austen"
  but `?author=Austen` does not. An empty `?author=` means no filter.
- **`PUT /books/{id}`** replaces the whole book, as `PUT` is defined to. The body
  must therefore be complete: `title` and `author` are required, and a `year` or
  `isbn` you leave out is cleared. It never creates a book; an unknown `id` is a `404`.
- **`DELETE /books/{id}`** returns `204` with no body.
- **`GET /health`** returns `{"status":"ok"}`, or `503` with `{"status":"unavailable"}`
  if the database cannot be reached.

### Errors

Every error has the same shape. Validation failures add a `details` object that
names each rejected field:

```json
{ "error": "validation failed", "details": { "title": "is required" } }
```

| Status | When                                                                                             |
|--------|--------------------------------------------------------------------------------------------------|
| `400`  | Validation failed; body is empty, is not valid JSON, is not a single JSON object, or a field has the wrong type; `{id}` is not an integer |
| `404`  | No book with that `id`; unknown route                                                            |
| `405`  | Method not supported on that path (the `Allow` header lists the supported ones)                  |
| `413`  | Request body larger than 1 MiB                                                                   |
| `500`  | Unexpected server error (details are logged, never sent to the client)                           |
| `503`  | `/health` cannot reach the database                                                              |

The request `Content-Type` is not checked, so plain `curl -d '{...}'` works.

### Examples

```sh
# Create a book
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}'
# HTTP/1.1 201 Created
# Location: /books/1
# {"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}

# Year and ISBN are optional
curl -X POST localhost:8080/books -d '{"title": "Emma", "author": "Jane Austen", "year": 1815}'
# {"id":2,"title":"Emma","author":"Jane Austen","year":1815,"isbn":""}

# List all books, then only one author's
curl localhost:8080/books
# [{"id":1,"title":"Dune", ...},{"id":2,"title":"Emma", ...}]
curl 'localhost:8080/books?author=Jane%20Austen'
# [{"id":2,"title":"Emma","author":"Jane Austen","year":1815,"isbn":""}]

# Get one book
curl localhost:8080/books/1
# {"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}

# Update a book (send the complete book)
curl -X PUT localhost:8080/books/2 \
  -d '{"title": "Emma", "author": "Jane Austen", "year": 1816, "isbn": "978-0141439587"}'
# {"id":2,"title":"Emma","author":"Jane Austen","year":1816,"isbn":"978-0141439587"}

# Delete a book
curl -i -X DELETE localhost:8080/books/1
# HTTP/1.1 204 No Content
curl -i localhost:8080/books/1
# HTTP/1.1 404 Not Found
# {"error":"book not found"}

# Validation: title and author are required
curl -i -X POST localhost:8080/books -d '{"title": "", "year": 1999}'
# HTTP/1.1 400 Bad Request
# {"error":"validation failed","details":{"author":"is required","title":"is required"}}
```

## Tests

```sh
go test ./...                # everything
go test -race -cover ./...   # with the race detector and coverage
```

The tests use real SQLite databases in temporary directories, so nothing is
mocked on the happy path:

- `internal/api`: every endpoint through the HTTP handler: status codes, response
  bodies, validation, the author filter, 404/405 handling, and failure paths
  (database errors, panics) using a fake store.
- `internal/store`: CRUD, ordering, case-insensitive filtering, ID reuse,
  persistence across reopen, and concurrent access to file and in-memory databases.
- `internal/book`: the validation rules, including their boundaries.
- `main_test.go`: configuration precedence, plus end-to-end runs that start the
  real server on a free port, exercise the whole API over HTTP, check graceful
  shutdown, and check that data survives a restart. It also runs the program
  itself as a child process to check exit codes and `SIGTERM`/`SIGINT` handling.

## Project layout

```
main.go             configuration, wiring and graceful shutdown
internal/book/      Book model, request input and its validation rules
internal/store/     SQLite persistence
internal/api/       HTTP routes, handlers, JSON helpers and middleware
```

## Design notes

- **Standard library only for HTTP.** Go 1.22's `net/http` routing supports
  method and path-parameter patterns (`GET /books/{id}`), so no web framework is
  needed. The `api` package depends on a small `BookStore` interface, which is
  what lets the tests inject failing stores.
- **`modernc.org/sqlite`** is a pure-Go SQLite driver, so `go build` works
  without CGO or a C toolchain. The database runs in WAL mode with a busy
  timeout, and the store uses a single pooled connection: SQLite allows one
  writer at a time anyway, and it keeps `:memory:` databases consistent.
- **IDs come from `AUTOINCREMENT`**, so the ID of a deleted book is never given
  to a different book.
- Queries are parameterised; the author filter uses `=`, not `LIKE`, so `%` and
  `_` in a query are ordinary characters.

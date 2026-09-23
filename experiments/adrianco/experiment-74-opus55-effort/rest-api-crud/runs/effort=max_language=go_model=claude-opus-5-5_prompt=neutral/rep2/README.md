# Book Collection API

A REST API service for managing a book collection, written in Go and backed by SQLite.

- HTTP: the Go standard library's `net/http`, using its method-and-path routing (Go 1.22+). No web framework.
- Storage: [modernc.org/sqlite](https://pkg.go.dev/modernc.org/sqlite), a pure-Go SQLite driver, so no C compiler or CGO is needed.

## Setup

Install Go 1.25 or later. The only dependency is the SQLite driver. `go` downloads it on the first build, or you can fetch it ahead of time with `go mod download`.

## Running

```sh
go run .
```

The server listens on port 8080 and keeps its data in `books.db` in the current directory, creating the file on first run. While the server runs, SQLite also keeps `books.db-wal` and `books.db-shm` next to it.

| Flag    | Environment variable | Default    | Meaning                                                  |
|---------|----------------------|------------|----------------------------------------------------------|
| `-addr` | `PORT` (port only)   | `:8080`    | Address to listen on                                     |
| `-db`   | `DB_PATH`            | `books.db` | SQLite database file, or `:memory:` for a throwaway one  |

Flags take precedence over environment variables:

```sh
PORT=9000 go run .
go run . -addr 127.0.0.1:9000 -db /tmp/books.db
```

To build and run a binary:

```sh
go build -o bookapi .
./bookapi
```

On Ctrl-C or SIGTERM the server stops accepting connections, lets in-flight requests finish, and then exits.

## API

| Method   | Path          | Success response                                    | Error statuses |
|----------|---------------|-----------------------------------------------------|----------------|
| `GET`    | `/health`     | 200 `{"status":"ok"}`                               | 503            |
| `POST`   | `/books`      | 201 with the new book and a `Location` header       | 400, 413       |
| `GET`    | `/books`      | 200 with an array of books; optional `?author=`     |                |
| `GET`    | `/books/{id}` | 200 with the book                                   | 404            |
| `PUT`    | `/books/{id}` | 200 with the updated book                           | 400, 404, 413  |
| `DELETE` | `/books/{id}` | 204, no body                                        | 404            |

### Books

```json
{"id": 1, "title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949, "isbn": "978-0452284234"}
```

| Field    | Type            | Rules                                     |
|----------|-----------------|-------------------------------------------|
| `id`     | integer         | Assigned by the server and never reused   |
| `title`  | string          | Required, at most 500 characters          |
| `author` | string          | Required, at most 300 characters          |
| `year`   | integer or null | Optional, from 1 to next year             |
| `isbn`   | string or null  | Optional, at most 32 characters           |

The server trims leading and trailing whitespace from strings and stores a blank ISBN as null. It ignores fields it doesn't recognize in request bodies, including `id`.

Some behavior to know about:

- **`PUT` replaces the whole book.** The body must be a complete book (title and author are required), and any optional field left out is cleared.
- **`?author=` matches part of the name, ignoring case.** For example, `?author=orwell` finds books by "George Orwell". Case matching covers ASCII letters only, because it uses SQLite's `lower()`.
- **An ID that isn't a positive integer** (for example `/books/abc`) gets 404, the same as an ID with no book.
- **Books are listed in ID order**, which is the order they were added.

### Errors

Every error response is a JSON object with an `error` message. A validation failure also lists each invalid field:

```json
{
  "error": "validation failed: title is required; author is required",
  "fields": {"title": "is required", "author": "is required"}
}
```

| Status | When                                                                  |
|--------|-----------------------------------------------------------------------|
| 400    | The body isn't valid JSON, a field has the wrong type, or validation fails |
| 404    | No book has that ID, or the path doesn't exist                        |
| 405    | The method isn't supported for the path (the `Allow` header lists those that are) |
| 413    | The request body is larger than 1 MiB                                 |
| 500    | Unexpected server error (the server logs the details but doesn't return them) |
| 503    | `/health` only: the database is unreachable                           |

### Examples

```sh
curl -i -X POST localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949,"isbn":"978-0452284234"}'
curl localhost:8080/books
curl 'localhost:8080/books?author=orwell'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"1984","author":"George Orwell","year":1949}'
curl -i -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

## Testing

```sh
go test ./...
go test -race -v ./...   # with the race detector and per-test output
```

The tests don't need a running server or any external service. Each test uses its own temporary SQLite database.

- `book_test.go`: unit tests of normalization and the validation rules.
- `store_test.go`: integration tests of the SQLite store. They cover create, read, update and delete, the author filter, persistence after reopening the database, IDs not being reused, and concurrent writes.
- `server_test.go`: HTTP tests of every endpoint. They cover status codes and JSON bodies, rejection of invalid or malformed input, 404 and 405 handling, and turning database errors and panics into 500 responses that don't expose internal details.
- `main_test.go`: tests of configuration parsing, plus an end-to-end test. It starts the real server on a free port, uses the API over HTTP, and checks that the server shuts down gracefully.

## Project layout

| File        | Contents                                                              |
|-------------|-----------------------------------------------------------------------|
| `main.go`   | Configuration, server startup and graceful shutdown                   |
| `server.go` | Routes, handlers, JSON handling, error responses and middleware       |
| `store.go`  | SQLite schema and data access                                         |
| `book.go`   | The book model and input validation                                   |

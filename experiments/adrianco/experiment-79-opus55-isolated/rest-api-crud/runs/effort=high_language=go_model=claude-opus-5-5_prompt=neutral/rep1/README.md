# Books API

A small REST service for managing a book collection, written in Go with the
standard library `net/http` router and SQLite for storage.

SQLite access uses [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite),
a pure-Go driver, so no C compiler or cgo is needed to build or run.

## Requirements

- Go 1.26 or newer

## Setup and run

```sh
go mod download      # fetch dependencies
go run .             # start the server on :8080, storing data in ./books.db
```

Or build a binary:

```sh
go build -o books .
./books -addr :9000 -db /var/lib/books/books.db
```

### Configuration

| Flag    | Environment variable | Default    | Description                                      |
|---------|----------------------|------------|--------------------------------------------------|
| `-addr` | `ADDR`               | `:8080`    | Address to listen on                             |
| `-db`   | `DB_PATH`            | `books.db` | SQLite database file (`:memory:` for throwaway)  |

Flags take precedence over environment variables. The database file and schema
are created on first start. The server shuts down gracefully on `SIGINT`/`SIGTERM`.

## Tests

```sh
go test ./...
```

The tests drive the real HTTP handler against an in-memory SQLite database, plus
a store test that checks data survives closing and reopening a database file.

## API

All request and response bodies are JSON. A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

| Method   | Path          | Description                  | Success          |
|----------|---------------|------------------------------|------------------|
| `GET`    | `/health`     | Health check (pings the DB)  | `200`            |
| `POST`   | `/books`      | Create a book                | `201` + the book |
| `GET`    | `/books`      | List books, ordered by ID    | `200` + an array |
| `GET`    | `/books/{id}` | Get one book                 | `200` + the book |
| `PUT`    | `/books/{id}` | Replace a book               | `200` + the book |
| `DELETE` | `/books/{id}` | Delete a book                | `204`, no body   |

### Fields and validation

| Field    | Type    | Rules                                             |
|----------|---------|---------------------------------------------------|
| `title`  | string  | Required; must not be blank                       |
| `author` | string  | Required; must not be blank                       |
| `year`   | integer | Optional, defaults to `0`; must not be negative   |
| `isbn`   | string  | Optional, defaults to `""`; stored as given       |

Leading and trailing whitespace is trimmed from the string fields. `id` is
assigned by the server; an `id` in a request body is ignored, as are any other
unknown fields.

`PUT` is a full replacement: `title` and `author` are required again, and
optional fields left out are reset to their defaults.

### Filtering

`GET /books?author=Frank+Herbert` returns only books by that author. The match
is on the whole name and ignores ASCII case. An empty `author` parameter is the
same as no filter.

### Errors

Errors are returned as JSON with an `error` message. Validation failures also
list the offending fields:

```json
{"error": "validation failed", "fields": {"title": "title is required"}}
```

| Status | When                                                                 |
|--------|----------------------------------------------------------------------|
| `400`  | Malformed JSON, wrong field type, failed validation, or a bad ID     |
| `404`  | No book with that ID, or an unknown route                            |
| `405`  | Method not supported on that path (see the `Allow` header)           |
| `413`  | Request body larger than 1 MiB                                       |
| `500`  | Unexpected server/database error                                     |
| `503`  | `/health` only: the database is unreachable                          |

### Examples

```sh
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl localhost:8080/books
curl 'localhost:8080/books?author=Frank+Herbert'
curl localhost:8080/books/1

curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'

curl -i -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

## Layout

| File          | Contents                                        |
|---------------|-------------------------------------------------|
| `main.go`     | Flags, server setup, graceful shutdown          |
| `handlers.go` | Routing, request decoding, JSON responses       |
| `store.go`    | SQLite schema and queries                       |
| `book.go`     | The `Book` type and input validation            |
| `*_test.go`   | HTTP integration tests and store tests          |

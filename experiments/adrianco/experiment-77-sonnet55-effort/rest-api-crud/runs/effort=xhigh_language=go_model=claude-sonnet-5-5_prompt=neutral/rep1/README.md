# Book Collection API

A small REST API for managing a book collection, written in Go using only the
standard library (`net/http`) plus [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite),
a pure-Go SQLite driver. No CGO or C toolchain is needed.

## Requirements

- Go 1.26 or newer (see `go` in `go.mod`)

## Setup and run

```sh
go mod download     # fetch dependencies (also happens automatically on build)
go run .            # serve on :8080, storing data in ./books.db
```

Or build a binary:

```sh
go build -o bookapi .
./bookapi
```

Configuration is through environment variables:

| Variable  | Default    | Meaning                                                  |
|-----------|------------|----------------------------------------------------------|
| `ADDR`    | `:8080`    | Address to listen on, e.g. `127.0.0.1:9000`              |
| `DB_PATH` | `books.db` | SQLite database file (created if missing); `:memory:` for a throwaway DB |

The server shuts down gracefully on `SIGINT` / `SIGTERM`.

## Tests

```sh
go test ./...
go test -race ./...   # optionally, with the race detector
```

The tests run against in-memory SQLite databases, so they need no setup and
leave no files behind. `internal/books` covers the store and validation;
`internal/api` drives the full HTTP API through `httptest`.

## API

All request and response bodies are JSON. Errors have the shape
`{"error": "message"}`, plus a `fields` object for validation failures.

A book:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719" }
```

| Method | Path           | Description                        | Success | Errors             |
|--------|----------------|------------------------------------|---------|--------------------|
| POST   | `/books`       | Create a book                      | 201     | 400, 413           |
| GET    | `/books`       | List books; optional `?author=`    | 200     |                    |
| GET    | `/books/{id}`  | Get one book                       | 200     | 400, 404           |
| PUT    | `/books/{id}`  | Replace a book                     | 200     | 400, 404, 413      |
| DELETE | `/books/{id}`  | Delete a book                      | 204     | 400, 404           |
| GET    | `/health`      | Health check (pings the database)  | 200     | 503 if DB is down  |

Unknown paths return 404 and unsupported methods return 405 (with an `Allow`
header), both as JSON.

### Fields and validation

| Field    | Rules                                                  |
|----------|--------------------------------------------------------|
| `title`  | **Required**, non-blank, at most 500 characters        |
| `author` | **Required**, non-blank, at most 200 characters        |
| `year`   | Optional integer, 0 to 9999 (0 means unspecified)      |
| `isbn`   | Optional string, at most 32 characters (format not checked) |

Leading and trailing whitespace is trimmed. Invalid input returns `400` and
lists every offending field:

```json
{ "error": "validation failed", "fields": { "title": "is required", "author": "is required" } }
```

Other `400` cases: malformed JSON, a field of the wrong type (e.g. `"year": "1999"`),
an empty body, or an `{id}` that is not a positive integer.

`PUT` replaces the whole record, so `title` and `author` are required again and
omitted optional fields are reset. `POST` also sets a `Location: /books/{id}` header.

`?author=` matches the author name exactly, ignoring case (`?author=jane austen`
finds "Jane Austen"). Results are ordered by ID; an empty result is `[]`.

### Example session

```sh
curl -i -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl localhost:8080/books
curl "localhost:8080/books?author=Frank%20Herbert"
curl localhost:8080/books/1

curl -X PUT localhost:8080/books/1 \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl -i -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

## Project layout

```
main.go                 config, server start-up, graceful shutdown
internal/books/         Book model, validation, SQLite store
internal/api/           HTTP routing, handlers, JSON helpers, logging/recovery middleware
```

The store uses a single database connection: SQLite allows one writer at a
time anyway, and this keeps `:memory:` databases (a separate database per
connection) correct. File databases use WAL mode and a 5-second busy timeout.

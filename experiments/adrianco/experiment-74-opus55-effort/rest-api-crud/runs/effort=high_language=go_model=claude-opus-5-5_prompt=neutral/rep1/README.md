# Book Collection API

A REST API for managing a book collection, written in Go. It uses the standard library
`net/http` router (Go 1.22+ method/path patterns) and stores data in SQLite through
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), a pure-Go driver, so no C compiler / cgo is needed.

## Requirements

- Go 1.22 or newer

## Setup and run

```bash
go mod download        # fetch dependencies
go run .               # starts on :8080 using ./books.db
```

Or build a binary:

```bash
go build -o bookapi .
PORT=9000 DB_PATH=/var/data/books.db ./bookapi
```

| Env var   | Default    | Meaning                                   |
|-----------|------------|-------------------------------------------|
| `PORT`    | `8080`     | TCP port to listen on                     |
| `DB_PATH` | `books.db` | SQLite file (created automatically)       |

The server shuts down gracefully on `SIGINT` / `SIGTERM`.

## Running the tests

```bash
go test ./...
go test -race -v ./...   # verbose, with the race detector
```

The tests are integration tests: each one starts the HTTP handler against a fresh
SQLite database in a temp directory. They cover the full CRUD lifecycle, the author
filter, validation, error status codes, the health check (up and down), persistence across
restarts, and concurrent writes.

## API

A book looks like this:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "0-441-17271-7" }
```

| Method & path         | Description                  | Success                    | Errors            |
|-----------------------|------------------------------|----------------------------|-------------------|
| `GET /health`         | Health check (pings the DB)  | `200 {"status":"ok",...}`  | `503`             |
| `POST /books`         | Create a book                | `201` + book + `Location`  | `400`, `413`      |
| `GET /books`          | List books (`?author=` filter) | `200` + array (may be `[]`) |                 |
| `GET /books/{id}`     | Get one book                 | `200` + book               | `400`, `404`      |
| `PUT /books/{id}`     | Replace a book               | `200` + book               | `400`, `404`, `413` |
| `DELETE /books/{id}`  | Delete a book                | `204` (no body)            | `400`, `404`      |

Errors are returned as JSON: `{"error": "book not found"}`. Validation failures also list the
problem fields:

```json
{ "error": "validation failed", "fields": { "title": "title is required" } }
```

### Validation rules

- `title` (required): non-empty after trimming whitespace, at most 500 characters.
- `author` (required): non-empty after trimming whitespace, at most 300 characters.
- `year` (optional): an integer from 0 to next year. Leave it out or send `null` for unknown.
- `isbn` (optional): 10 or 13 digits. Hyphens and spaces are allowed, and an ISBN-10 may end in
  `X`. The checksum is not checked.
- The body must be a single JSON object no larger than 1 MiB.
- `{id}` must be a positive integer. Anything else returns `400`.

`PUT` replaces the whole book, so any optional field you leave out is cleared.

### Author filter

`GET /books?author=herbert` returns books whose author contains the given text. The match
ignores case for ASCII letters. `%` and `_` in the query are matched as literal characters,
not as wildcards. Results are ordered by `id`.

### Examples

```bash
curl -X POST localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"0-441-17271-7"}'
curl 'localhost:8080/books?author=herbert'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

## Project layout

| File               | Purpose                                            |
|--------------------|----------------------------------------------------|
| `main.go`          | Configuration, HTTP server, graceful shutdown      |
| `handlers.go`      | Routes, request decoding, validation, JSON output  |
| `store.go`         | `Store` interface and the SQLite implementation    |
| `handlers_test.go` | Integration and unit tests                         |

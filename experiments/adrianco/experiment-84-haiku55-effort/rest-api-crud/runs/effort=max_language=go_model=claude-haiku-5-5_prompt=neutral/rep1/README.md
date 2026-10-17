# Book Collection API

A REST API for managing a book collection. It is written in Go with the
standard library's `net/http` and stores books in an SQLite file. The SQLite
driver is pure Go (`modernc.org/sqlite`), so no C compiler is needed.

## Requirements

- Go 1.26 or newer. This is the minimum that `modernc.org/sqlite` v1.60.1 requires.

## Setup

```sh
go mod download
```

## Run

```sh
go run . -addr :8080 -db books.db
```

Or build a binary and run it:

```sh
go build -o bookapi .
./bookapi -addr :8080 -db books.db
```

| Flag   | Default   | Description                                  |
|--------|-----------|----------------------------------------------|
| `-addr`| `:8080`   | HTTP listen address                          |
| `-db`  | `books.db`| SQLite database file, created if it is missing |

The server shuts down gracefully on `SIGINT` or `SIGTERM`, giving in-flight
requests up to 10 seconds to finish.

## API

Responses are JSON, apart from `204 No Content` (which has no body) and the
redirects that `net/http` issues for unclean paths such as `/books//`. A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

`year` and `isbn` are `null` when they are unknown.

| Method   | Path              | Success                    | Description                          |
|----------|-------------------|----------------------------|--------------------------------------|
| `POST`   | `/books`          | `201 Created` + `Location` | Create a book                        |
| `GET`    | `/books`          | `200 OK`                   | List books; `?author=` filters them  |
| `GET`    | `/books/{id}`     | `200 OK`                   | Get one book                         |
| `PUT`    | `/books/{id}`     | `200 OK`                   | Replace a book                       |
| `DELETE` | `/books/{id}`     | `204 No Content`           | Delete a book                        |
| `GET`    | `/health`         | `200 OK` or `503`          | Health check, including the database |

### Request body (POST and PUT)

```json
{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}
```

- `title` and `author` are **required**. Surrounding whitespace is trimmed, and each value can be at most 500 characters.
- `year` is optional. When it is present it must be a whole number from 1 to next calendar year, so forthcoming titles are allowed.
- `isbn` is optional. Hyphens and spaces are removed. The result must be a valid ISBN-10 (its last character may be `X`) or ISBN-13 (starting `978` or `979`), with a correct check digit. It is stored in that canonical form. A blank value counts as absent.
- Unknown fields are rejected with `400`, so a misspelt field name is not silently dropped.
- Request bodies are limited to 1 MiB.

`PUT` replaces the whole record. If `year` or `isbn` is left out, it is cleared.

### Filtering

`GET /books?author=herbert` returns the books whose author contains the text,
ignoring case. Surrounding spaces are trimmed, and `%` and `_` are matched
literally. An empty `?author=` returns every book. Results are in ID order.

IDs are never reused. Once a book is deleted, its ID stays retired, so a
client holding an old ID gets `404`, never someone else's book.

### Errors

Errors use the same JSON shape every time:

```json
{"error": "validation failed", "fields": {"title": "is required", "isbn": "must be a valid ISBN-10 or ISBN-13"}}
```

`fields` appears only for validation errors.

| Status | When                                                                 |
|--------|----------------------------------------------------------------------|
| `400`  | Invalid JSON, validation failed, or an `{id}` that is not a positive integer |
| `404`  | No book with that ID, or no such route                               |
| `405`  | Method not supported on that path; the `Allow` header lists the valid methods |
| `413`  | Request body larger than 1 MiB                                       |
| `500`  | Unexpected server error. It is logged, and the response is generic   |
| `503`  | `/health` cannot reach the database                                  |

### Examples

```sh
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"}'

# List, and filter by author
curl localhost:8080/books
curl 'localhost:8080/books?author=herbert'

# Get, replace, delete
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -i -X DELETE localhost:8080/books/1

# Health
curl localhost:8080/health
```

## Tests

```sh
go test ./...
go test -race ./...   # the race detector requires cgo
```

- `book_test.go` covers the validation rules and the ISBN check digits.
- `store_test.go` covers SQLite persistence, the author filter, ID handling, and concurrent writes. Each test uses its own database file in a temporary directory.
- `api_test.go` covers every endpoint and error path through the HTTP handler.

## Project layout

```
main.go     flags, startup, and graceful shutdown
api.go      routing, handlers, JSON responses, and error responses
book.go     the Book type, input validation, and ISBN checks
store.go    SQLite persistence
```

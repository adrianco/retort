# Book Collection API

A small REST API for managing a book collection, written in Go with the
standard library (`net/http`) and an embedded SQLite database
([`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), a pure-Go driver,
so **no C compiler or system SQLite is needed**).

## Requirements

- Go 1.26 or newer (see `go.mod`)

## Setup and run

```sh
go build -o bookapi .
./bookapi                       # listens on :8080, stores data in ./books.db
```

or, without building a binary: `go run .`

| Flag    | Environment | Default    | Meaning                          |
|---------|-------------|------------|----------------------------------|
| `-addr` | `ADDR`      | `:8080`    | HTTP listen address              |
| `-db`   | `DB_PATH`   | `books.db` | SQLite file (`:memory:` for a throwaway database) |

The database file and schema are created on first start. The server shuts down
gracefully on `SIGINT`/`SIGTERM`.

## Tests

```sh
go test ./...            # add -race for the race detector
```

The suite covers the SQLite store (CRUD, filtering, persistence, concurrent
writes) and the HTTP API end to end (all endpoints, validation, error
responses, 404/405 handling, failure paths).

## API

All request and response bodies are JSON. A book looks like:

```json
{ "id": 1, "title": "1984", "author": "George Orwell", "year": 1949, "isbn": "9780451524935" }
```

| Field    | Type    | Rules                                                   |
|----------|---------|---------------------------------------------------------|
| `id`     | integer | Assigned by the server; ignored if sent in a request    |
| `title`  | string  | **Required**, non-blank, up to 255 characters           |
| `author` | string  | **Required**, non-blank, up to 255 characters           |
| `year`   | integer | Optional, 1–9999; returned as `null` when not set       |
| `isbn`   | string  | Optional free-form text, up to 32 characters (format is not checked) |

Leading and trailing whitespace in strings is trimmed.

### Endpoints

| Method   | Path           | Success                    | Description                                   |
|----------|----------------|----------------------------|-----------------------------------------------|
| `POST`   | `/books`       | `201` + book, `Location`   | Create a book                                 |
| `GET`    | `/books`       | `200` + array of books     | List books, optionally `?author=NAME`         |
| `GET`    | `/books/{id}`  | `200` + book               | Get one book                                  |
| `PUT`    | `/books/{id}`  | `200` + updated book       | Replace a book (same rules as create)         |
| `DELETE` | `/books/{id}`  | `204`, no body             | Delete a book                                 |
| `GET`    | `/health`      | `200` `{"status":"ok"}`    | Health check (`503` if the database is unreachable) |

Notes:

- `PUT` is a full replacement: `title` and `author` are required, and omitting
  `year` or `isbn` clears them.
- `?author=` matches the whole author name, ignoring ASCII case (`george orwell`
  matches `George Orwell`; `Orwell` does not). Results are ordered by `id`, and
  an empty result is `[]`.

### Errors

Errors are JSON of the form `{"error": "message"}`. Validation failures also
include per-field `details`:

```json
{ "error": "validation failed", "details": { "title": "is required", "author": "is required" } }
```

| Status | When                                                              |
|--------|-------------------------------------------------------------------|
| `400`  | Invalid/missing fields, malformed or empty JSON, non-positive-integer `{id}` |
| `404`  | No such book, or unknown route                                    |
| `405`  | Method not supported on the route (an `Allow` header is sent)     |
| `413`  | Request body larger than 1 MiB                                    |
| `500`  | Unexpected server error (details are logged, not returned)        |

### Example session

```sh
curl -i -X POST localhost:8080/books \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"9780451524935"}'

curl 'localhost:8080/books?author=george%20orwell'
curl localhost:8080/books/1

curl -X PUT localhost:8080/books/1 \
  -d '{"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949}'

curl -i -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

## Project layout

```
main.go                    flags, server start-up, graceful shutdown
internal/store/store.go    SQLite persistence (schema, CRUD)
internal/api/api.go        routing and handlers
internal/api/request.go    body decoding and validation
internal/api/response.go   JSON responses, logging and panic-recovery middleware
```

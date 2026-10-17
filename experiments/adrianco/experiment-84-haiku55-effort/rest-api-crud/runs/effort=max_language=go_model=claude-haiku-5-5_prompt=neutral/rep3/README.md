# bookapi

A REST API for managing a book collection. It is written in Go using the
standard library's HTTP server and router, and stores data in SQLite. The
SQLite driver is pure Go, so no C compiler is needed.

## Requirements

- Go 1.26.0 or newer (the version the dependencies require)

## Setup

```sh
go mod download
```

## Run

```sh
go run ./cmd/bookapi
```

The server listens on `:8080` and keeps its data in `books.db` in the current
directory. The database and its table are created on first start.

| Setting              | Flag    | Environment variable | Default    |
| -------------------- | ------- | -------------------- | ---------- |
| HTTP listen address  | `-addr` | `BOOKAPI_ADDR`       | `:8080`    |
| SQLite database file | `-db`   | `BOOKAPI_DB`         | `books.db` |

A flag takes precedence over its environment variable. To build a binary and
run it on another port:

```sh
go build -o bin/bookapi ./cmd/bookapi
mkdir -p data
./bin/bookapi -addr :9000 -db ./data/books.db
```

The directory that holds the database file must already exist. The file itself
is created on first start.

The server shuts down gracefully on `SIGINT` or `SIGTERM`.

## API

All request and response bodies are JSON.

| Method   | Path              | Purpose                                  | Success                 | Errors           |
| -------- | ----------------- | ---------------------------------------- | ----------------------- | ---------------- |
| `POST`   | `/books`          | Create a book                            | `201` with `Location`   | `400`, `413`     |
| `GET`    | `/books`          | List books; optional `?author=` filter   | `200`                   |                  |
| `GET`    | `/books/{id}`     | Get one book                             | `200`                   | `400`, `404`     |
| `PUT`    | `/books/{id}`     | Replace a book                           | `200`                   | `400`, `404`, `413` |
| `DELETE` | `/books/{id}`     | Delete a book                            | `204` (no body)         | `400`, `404`     |
| `GET`    | `/health`         | Health check                             | `200`                   | `503`            |

Any other path returns `404`, and any other method on a known path returns
`405` with an `Allow` header. Both are JSON responses like the rest.

### Book fields

| Field    | Type    | Required | Rules                                                                 |
| -------- | ------- | -------- | --------------------------------------------------------------------- |
| `id`     | integer | (output) | Assigned by the server. Never reused after a delete.                  |
| `title`  | string  | yes      | Non-blank after trimming. At most 500 characters.                     |
| `author` | string  | yes      | Non-blank after trimming. At most 200 characters.                     |
| `year`   | integer | no       | Publication year. `0` or omitted means unknown. Otherwise between `0` and next year. |
| `isbn`   | string  | no       | Empty, or an ISBN-10 or ISBN-13 in shape. Hyphens and spaces are allowed. The check digit is not verified. |

Leading and trailing whitespace is trimmed from text fields before they are
stored. Unknown JSON fields, such as an `id` sent back by a client, are ignored.

Example book:

```json
{"id":1,"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0547928227"}
```

### Behaviour notes

- **`POST` and `PUT` take the full book.** `PUT` replaces every field, as HTTP
  specifies. An omitted `year` or `isbn` is cleared. To change one field, send
  the whole book.
- **`?author=` is a case-insensitive substring match.** `?author=tolkien`
  matches "J.R.R. Tolkien". Surrounding spaces are ignored. Results are ordered
  by `id`.
- **Empty lists are `[]`**, never `null`.
- **`Content-Type` is not required** on requests. The body is parsed as JSON
  either way.

### Errors

Every error response has this shape:

```json
{"error":"book not found"}
```

Validation failures also list each invalid field under `details`:

```json
{"error":"validation failed","details":{"author":"is required"}}
```

Status codes:

- `400` — malformed JSON, a body that is not a single object, a non-positive or
  non-integer `{id}`, or a validation failure
- `404` — no book with that `id`, or no such endpoint
- `405` — method not allowed on this path
- `413` — request body larger than 1 MiB
- `500` — unexpected server error (details are logged, not returned)
- `503` — `/health` could not reach the database

## Examples

```sh
# Create
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

# List everything, or filter by author
curl http://localhost:8080/books
curl 'http://localhost:8080/books?author=herbert'

# Get, replace and delete
curl http://localhost:8080/books/1
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -i -X DELETE http://localhost:8080/books/1

# Health
curl http://localhost:8080/health
```

## Tests

```sh
go test ./...
```

The suite covers:

- **`internal/book`** — validation rules, including the field limits, year
  bounds, ISBN shapes and whitespace trimming.
- **`internal/store`** — CRUD against a real SQLite file, the author filter,
  `ErrNotFound` on missing rows, and data surviving a reopen.
- **`internal/api`** — HTTP integration tests. They run the full router, with
  logging and panic recovery, over a live test server. They cover status codes,
  JSON bodies and error envelopes, the `Location` header, `Allow` on `405`,
  the body size limit, and the health endpoint.

## Project layout

```
cmd/bookapi/        entry point: configuration, server lifecycle
internal/book/      Book model, request input and validation rules
internal/store/     SQLite persistence
internal/api/       routing, handlers, middleware, JSON responses
```

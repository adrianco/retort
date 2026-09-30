# Book Collection API

A small REST API for managing a collection of books. It is written in Go using
only the standard library's `net/http` for HTTP (Go 1.22+ `ServeMux` routes on
method and `{id}` path wildcards, so no web framework is needed) and stores its
data in an embedded SQLite database through the pure-Go driver
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite). No CGO, C
compiler or system SQLite installation is required.

## Requirements

- Go 1.26 or newer (required by the SQLite driver).

Dependencies are downloaded automatically by the Go toolchain on the first
build; there is nothing else to install.

## Setup and run

From the repository root:

```sh
go run .
```

The server listens on `:8080` and keeps its data in `books.db` in the current
directory, which is created on first start. Press Ctrl+C to stop it: requests
that are already in flight get up to 10 seconds to finish, and a second Ctrl+C
during that time stops the server immediately.

To build a binary instead:

```sh
go build -o bookapi .
./bookapi
```

### Configuration

| Setting        | Flag              | Environment variable | Default    |
| -------------- | ----------------- | -------------------- | ---------- |
| Listen address | `-addr host:port` | `PORT` (port only)   | `:8080`    |
| Database file  | `-db path`        | `DB_PATH`            | `books.db` |

Flags take precedence over environment variables. For example:

```sh
PORT=9000 go run .
go run . -addr 127.0.0.1:9000 -db /tmp/books.db   # reachable from this machine only
go run . -db :memory:                             # throwaway in-memory database
```

The API has no authentication and listens on all interfaces by default. Bind it
to `127.0.0.1` (as above) when it must not be reachable from other machines.
Because the request `Content-Type` is not enforced (see below), a web page open
in a browser on the same machine can also make it create books, although it
cannot read the answers.

## API

Request and response bodies are JSON. Requests should send
`Content-Type: application/json`, but the header is not enforced, so clients
that leave it out still work. The API's own responses are all
`Content-Type: application/json`, except `204 No Content`, which has no body.
Go's HTTP server itself answers two situations before the API is involved, and
those replies are not JSON: a request line it rejects outright, such as an
invalid `%` escape in the path (plain-text `400`), and a redirect for a
non-canonical path such as `//books` or `/books/../health` (`307`).

| Method | Path          | Description                                   | Success                          |
| ------ | ------------- | --------------------------------------------- | -------------------------------- |
| POST   | `/books`      | Create a book                                 | `201 Created` + `Location` header |
| GET    | `/books`      | List all books, optionally filtered by author | `200 OK`                         |
| GET    | `/books/{id}` | Get one book                                  | `200 OK`                         |
| PUT    | `/books/{id}` | Replace (update) a book                       | `200 OK`                         |
| DELETE | `/books/{id}` | Delete a book                                 | `204 No Content`                 |
| GET    | `/health`     | Health check, including a database ping       | `200 OK`, or `503` if the database is unreachable |

### The book resource

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441172719"
}
```

| Field    | Type            | Rules                                                                    |
| -------- | --------------- | ------------------------------------------------------------------------ |
| `id`     | integer         | Assigned by the server and never reused. Ignored if sent in a request.   |
| `title`  | string          | **Required**, not blank, at most 500 characters.                         |
| `author` | string          | **Required**, not blank, at most 500 characters.                         |
| `year`   | integer or null | Optional, from 0 to 9999.                                                |
| `isbn`   | string or null  | Optional, at most 32 characters. Stored as given: no format check, and it need not be unique. |

Surrounding whitespace in `title`, `author` and `isbn` is trimmed, and a blank
`isbn` counts as not provided. These three text fields must not contain control
characters (NUL, newlines, escape sequences and the like). Optional fields that
are not set are returned as `null`. Unknown fields in a request body are
ignored.

### Endpoints

**Create** — `POST /books`

```sh
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```

```
HTTP/1.1 201 Created
Location: /books/1

{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}
```

**List** — `GET /books`, or `GET /books?author=Frank%20Herbert`

Returns a JSON array ordered by ID (`[]` when there is nothing to return). The
`author` filter is an exact match on the whole author name that ignores case
(ASCII letters); it does not match part of a name. An empty `author` value
means no filter.

```sh
curl localhost:8080/books
curl 'localhost:8080/books?author=frank%20herbert'
```

**Get** — `GET /books/{id}`

```sh
curl localhost:8080/books/1
```

**Update** — `PUT /books/{id}`

`PUT` replaces the whole book, so send every field you want to keep: optional
fields left out of the request are cleared. `title` and `author` are required,
as when creating.

```sh
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
```

```
{"id":1,"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":null}
```

**Delete** — `DELETE /books/{id}`

```sh
curl -i -X DELETE localhost:8080/books/1     # 204 No Content
```

**Health** — `GET /health`

```sh
curl localhost:8080/health                   # {"status":"ok"}
```

### Errors

Errors are JSON objects with an `error` message. Validation failures also list
the offending fields under `details`:

```
HTTP/1.1 400 Bad Request

{"error":"title is required; author is required","details":{"author":"is required","title":"is required"}}
```

| Status | When                                                                                      |
| ------ | ----------------------------------------------------------------------------------------- |
| 400    | Validation failure, malformed or wrongly typed JSON, an `{id}` that is not a positive integer, or a malformed query string |
| 404    | No book with that ID, or an unknown endpoint                                              |
| 405    | Method not supported on that endpoint (the `Allow` header lists the supported ones)       |
| 413    | Request body larger than 1 MiB                                                            |
| 499    | Only ever seen in the log: the client hung up before the reply, so nobody received it     |
| 500    | Unexpected server error. The response is generic; the details are written to the log      |
| 503    | `/health` only: the database cannot be reached                                            |

## Tests

```sh
go test ./...            # everything
go test -race ./...      # with the race detector
go test -cover ./...     # with coverage
```

The suite uses temporary SQLite databases, so it never touches `books.db`. It
covers:

- the validation rules and their boundaries (`internal/book`);
- the SQLite store: CRUD, the author filter, ID handling, persistence across
  reopening, concurrent use, and unusual file names (`internal/sqlite`);
- every endpoint through the HTTP handler: status codes, JSON bodies, headers,
  validation and malformed-input errors, 404/405 responses, and the 500 and
  panic-recovery paths (`internal/api`);
- two fuzz targets in `internal/api` asserting that no request body, `?author=`
  value or `{id}` segment can provoke a server error. `go test` runs their seed
  inputs; to explore further run, for example,
  `go test ./internal/api -run '^$' -fuzz FuzzBookBody -fuzztime 1m`;
- the whole application over real HTTP on a loopback port: configuration,
  graceful shutdown, and data surviving a restart (`main_test.go`). These tests
  skip themselves if the environment does not allow listening on a port.

## Project layout

```
main.go             entry point: flags and environment, wiring, graceful shutdown
internal/book/      the Book model and the input normalisation and validation rules
internal/sqlite/    SQLite-backed store: schema, CRUD, author filter
internal/api/       HTTP routing, handlers, JSON helpers, logging and panic-recovery middleware
```

Tests sit next to the code they cover, in `*_test.go` files.

## Design notes

- **One SQLite connection.** SQLite allows a single writer at a time, so the
  store uses one connection. Concurrent requests queue instead of failing with
  `SQLITE_BUSY`, and an in-memory database stays one database.
- **IDs are never reused.** The table uses `AUTOINCREMENT`, so a deleted book's
  ID is not handed to a new book.
- **`PUT` is a full replacement**, as HTTP defines it; there is no `PATCH`.
- **Database path is a literal file name.** Characters such as `?` and `#` in
  `-db` are not interpreted as URI or driver options.

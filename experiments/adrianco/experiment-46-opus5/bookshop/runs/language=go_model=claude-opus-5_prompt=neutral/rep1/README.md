# bookapi

A small REST API for managing a book collection, written in Go and backed by an
embedded SQLite database.

## Requirements

- Go 1.22 or newer (developed against Go 1.26)

No C toolchain or system SQLite install is needed — the service uses
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), a pure-Go SQLite
implementation, so `CGO_ENABLED=0` builds work out of the box.

## Setup and run

```bash
go mod download        # fetch dependencies
go build -o bookapi .  # build
./bookapi              # run on :8080, storing data in ./books.db
```

Or run without building an artifact:

```bash
go run .
```

The database file is created automatically on first start.

### Configuration

| Flag          | Environment variable | Default    | Description                              |
| ------------- | -------------------- | ---------- | ---------------------------------------- |
| `-addr`       | `ADDR`               | `:8080`    | Address to listen on                     |
| `-db`         | `DB_PATH`            | `books.db` | Path to the SQLite file (`:memory:` works) |
| `-log-level`  | `LOG_LEVEL`          | `info`     | `debug`, `info`, `warn` or `error`       |

Flags take precedence over environment variables.

```bash
./bookapi -addr 127.0.0.1:9000 -db /var/lib/books/books.db
```

The server shuts down gracefully on `SIGINT` / `SIGTERM`, draining in-flight
requests for up to 10 seconds.

## Tests

```bash
go test ./...          # unit + integration tests
go test -race ./...    # also exercise the concurrency test under the race detector
go test -cover ./...
```

The integration tests spin up the full HTTP stack with `httptest` against a
throwaway SQLite file in a temp directory, so they exercise real routing,
serialization and persistence rather than mocks.

## API

All responses are JSON. Errors use a consistent shape:

```json
{ "error": "validation failed", "details": ["title is required"] }
```

### Book resource

| Field        | Type     | Notes                                                     |
| ------------ | -------- | --------------------------------------------------------- |
| `id`         | integer  | Assigned by the server                                    |
| `title`      | string   | **Required**, trimmed, max 512 characters                 |
| `author`     | string   | **Required**, trimmed, max 256 characters                 |
| `year`       | integer  | Optional; `0` means unknown. Must be ≤ next calendar year |
| `isbn`       | string   | Optional; ISBN-10 or ISBN-13, check digit validated       |
| `created_at` | RFC 3339 | Set on create                                             |
| `updated_at` | RFC 3339 | Refreshed on update                                       |

ISBNs are normalized before storage — hyphens and spaces are stripped, and a
trailing `x` is upper-cased — so `978-0-441-01359-3` and `9780441013593` are the
same book. ISBNs are unique across the collection; books without one are exempt.

### Endpoints

| Method   | Path          | Success        | Description                        |
| -------- | ------------- | -------------- | ---------------------------------- |
| `GET`    | `/health`     | `200`          | Liveness check (pings the database) |
| `POST`   | `/books`      | `201` + `Location` | Create a book                  |
| `GET`    | `/books`      | `200`          | List books, optional `?author=`    |
| `GET`    | `/books/{id}` | `200`          | Fetch one book                     |
| `PUT`    | `/books/{id}` | `200`          | Replace a book                     |
| `DELETE` | `/books/{id}` | `204`          | Delete a book                      |

`PUT` is a full replacement: fields you omit are reset to their zero value.

`?author=` matches case-insensitively on any part of the author name, so
`?author=gibson` finds "William Gibson". SQL wildcards in the query are escaped
and matched literally.

### Status codes

| Code  | When                                                            |
| ----- | --------------------------------------------------------------- |
| `400` | Validation failure, malformed/unknown JSON fields, or a non-numeric id |
| `404` | No book with that id, or no such route                           |
| `405` | Route exists but not for that method (includes an `Allow` header) |
| `409` | The ISBN is already registered to another book                   |
| `413` | Request body over 1 MiB                                          |
| `415` | `Content-Type` is present and is not `application/json`          |
| `503` | The database is unreachable (`/health` only)                     |

## Examples

```bash
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-01359-3"}'
# HTTP/1.1 201 Created
# Location: /books/1
# {"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593",
#  "created_at":"2026-07-24T18:54:46.279Z","updated_at":"2026-07-24T18:54:46.279Z"}

# List, and filter by author
curl localhost:8080/books
curl 'localhost:8080/books?author=herbert'

# Fetch one
curl localhost:8080/books/1

# Replace
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Revised)","author":"Frank Herbert","year":1965}'

# Delete
curl -i -X DELETE localhost:8080/books/1   # 204 No Content

# Validation failure
curl -X POST localhost:8080/books -H 'Content-Type: application/json' -d '{"year":1984}'
# {"error":"validation failed","details":["title is required","author is required"]}
```

## Layout

| File            | Contents                                                    |
| --------------- | ----------------------------------------------------------- |
| `main.go`       | Flag/env parsing, server lifecycle, graceful shutdown       |
| `server.go`     | Routes, handlers, request decoding, JSON responses          |
| `middleware.go` | Request logging, panic recovery, JSON-ified 404/405         |
| `store.go`      | SQLite schema and CRUD                                      |
| `book.go`       | The `Book` model, validation and ISBN normalization         |

### Design notes

- **Routing** uses the standard library's `http.ServeMux` method patterns
  (Go 1.22+), so there is no third-party web framework — only the SQLite driver
  is an external dependency.
- **Validation** collects every problem in one pass instead of failing on the
  first, so a client fixes everything in one round trip. Unknown JSON fields are
  rejected, which turns typos like `"tittle"` into a clear `400` rather than a
  silently missing title.
- **Concurrency**: the connection pool is capped at one writer and the busy
  timeout is set to 5 s, which keeps SQLite free of "database is locked" errors
  under parallel handlers; WAL mode is enabled for file-backed databases.
- **Timestamps** are stored as RFC 3339 text in UTC and parsed explicitly, so
  behaviour does not depend on driver-specific time conversion.

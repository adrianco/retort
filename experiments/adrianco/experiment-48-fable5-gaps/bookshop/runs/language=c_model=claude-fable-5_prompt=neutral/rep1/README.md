# Book Collection REST API (C + SQLite)

A small REST API for managing a book collection, written in plain C (C11).
It uses a minimal built-in HTTP/1.1 server on POSIX sockets — no web
framework — and stores data in SQLite.

## Requirements

- A C compiler (clang or gcc) and `make`
- SQLite3 development library (`-lsqlite3`; preinstalled on macOS, on
  Debian/Ubuntu install `libsqlite3-dev`)
- `curl` (only needed to run the integration tests)

## Build and run

```sh
make            # builds ./bookapi
./bookapi       # listens on port 8080, database file ./books.db
```

Port and database path can be set by argument or environment variable:

```sh
./bookapi 9090 /tmp/mybooks.db
PORT=9090 DB_PATH=/tmp/mybooks.db ./bookapi
```

## API

All responses are JSON. A book looks like:

```json
{"id":1,"title":"The Mythical Man-Month","author":"Fred Brooks","year":1975,"isbn":"978-0201835953"}
```

`title` and `author` are required non-empty strings; `year` (integer) and
`isbn` (string) are optional and returned as `null` when unset.

| Method | Path            | Description                          | Status codes        |
|--------|-----------------|--------------------------------------|---------------------|
| GET    | `/health`       | Health check: `{"status":"ok"}`      | 200                 |
| POST   | `/books`        | Create a book                        | 201, 400            |
| GET    | `/books`        | List all books; `?author=` filters by exact author | 200  |
| GET    | `/books/{id}`   | Get one book                         | 200, 404            |
| PUT    | `/books/{id}`   | Replace a book (same validation as create) | 200, 400, 404 |
| DELETE | `/books/{id}`   | Delete a book                        | 204, 404            |

Validation failures and unknown routes return a JSON error body such as
`{"error":"title is required and must be a non-empty string"}` with the
appropriate status code (400, 404, or 405 for unsupported methods).

### Examples

```sh
curl http://localhost:8080/health

curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Dispossessed","author":"Ursula K. Le Guin","year":1974}'

curl 'http://localhost:8080/books?author=Ursula%20K.%20Le%20Guin'
curl http://localhost:8080/books/1

curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Dispossessed","author":"Ursula K. Le Guin","year":1974,"isbn":"978-0060512750"}'

curl -X DELETE http://localhost:8080/books/1
```

## Tests

```sh
make test
```

This runs:

- `test_unit` — unit tests for the JSON reader, book payload validation,
  query-string parsing, and JSON output encoding (43 checks).
- `test_api.sh` — integration tests that start the server on a test port
  with a throwaway database and exercise the full CRUD lifecycle,
  validation errors, the author filter, and error routing via `curl`
  (34 checks).

## Source layout

| File          | Purpose                                              |
|---------------|------------------------------------------------------|
| `main.c`      | Socket accept loop, configuration                    |
| `http.c/.h`   | HTTP request parsing, response writing, URL decoding |
| `api.c/.h`    | Routing, handlers, input validation                  |
| `db.c/.h`     | SQLite storage layer and book JSON serialization     |
| `json.c/.h`   | Minimal JSON object reader and string-buffer helpers |
| `test_unit.c` | Unit tests                                           |
| `test_api.sh` | End-to-end integration tests                         |

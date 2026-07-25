# books-api

A small REST service for managing a book collection, written in C++17 with no
third-party dependencies: an embedded HTTP/1.1 server (POSIX sockets), a
hand-rolled JSON parser/serializer, and SQLite for storage.

## Requirements

- A C++17 compiler (clang or GCC)
- CMake ≥ 3.16
- SQLite3 development headers
  - macOS: included with the Xcode Command Line Tools (`xcode-select --install`)
  - Debian/Ubuntu: `sudo apt install libsqlite3-dev`
  - Fedora: `sudo dnf install sqlite-devel`

## Build

```sh
cmake -S . -B build
cmake --build build -j
```

This produces `build/books_api` (the service) and `build/books_tests` (the test
suite).

## Run

```sh
./build/books_api                     # http://127.0.0.1:8080, database ./books.db
./build/books_api --port 9000 --db /var/lib/books.db
./build/books_api --host 0.0.0.0      # listen on all interfaces
./build/books_api --db :memory: --quiet
```

| Option | Environment variable | Default | Description |
| --- | --- | --- | --- |
| `--host <address>` | `HOST` | `127.0.0.1` | Interface to bind |
| `--port <number>` | `PORT` | `8080` | Port to listen on (`0` picks a free one) |
| `--db <path>` | `BOOKS_DB` | `books.db` | SQLite file, or `:memory:` |
| `--quiet` | – | off | Disable per-request access logging |

The schema is created automatically on first start. `SIGINT` (Ctrl-C) or
`SIGTERM` triggers a graceful shutdown that drains in-flight requests.

## Test

```sh
./build/books_tests            # run everything
./build/books_tests store      # run tests whose name contains "store"
ctest --test-dir build --output-on-failure
```

49 cases cover JSON parsing/serialisation, input validation, the SQLite store,
HTTP routing, and end-to-end request/response flows against a real server bound
to an ephemeral port — including keep-alive pipelining, oversized
request rejection, and a concurrency check with 8 client threads.

## API

All responses are JSON, except `204 No Content` on delete.

### `GET /health`

```sh
curl localhost:8080/health
# 200 {"database":"ok","status":"ok"}
```

Returns `503` with `{"status":"degraded"}` if the database is not reachable.

### `POST /books`

`title` and `author` are required; `year` and `isbn` are optional.

```sh
curl -X POST localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

```
201 Created
Location: /books/1

{"author":"Frank Herbert","created_at":"2026-07-24T20:44:25.124Z","id":1,
 "isbn":"9780441013593","title":"Dune","updated_at":"2026-07-24T20:44:25.124Z","year":1965}
```

### `GET /books` and `GET /books?author=<name>`

Returns a JSON array ordered by id. The `author` filter is an exact match but
case-insensitive; a blank value is ignored.

```sh
curl localhost:8080/books
curl 'localhost:8080/books?author=frank%20herbert'
```

### `GET /books/{id}`

```sh
curl localhost:8080/books/1     # 200, or 404 {"error":"book not found"}
```

### `PUT /books/{id}`

A full replacement: `title` and `author` are required, and omitted optional
fields are cleared to `null`.

```sh
curl -X PUT localhost:8080/books/1 \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
```

### `DELETE /books/{id}`

```sh
curl -X DELETE localhost:8080/books/1     # 204 No Content, or 404
```

### Status codes

| Code | When |
| --- | --- |
| `200` | Successful read or update |
| `201` | Book created (with a `Location` header) |
| `204` | Book deleted |
| `400` | Malformed JSON, failed validation, or a non-numeric id |
| `404` | Unknown book or unknown route |
| `405` | Known path, unsupported method (with an `Allow` header) |
| `413` | Request body over 1 MiB |
| `500` | Unexpected server-side failure |
| `503` | Database unavailable (health check only) |

Validation failures list every offending field at once:

```sh
curl -X POST localhost:8080/books -d '{"author":"Nobody","year":"soon"}'
```

```json
{"details":[{"field":"title","message":"is required"},
            {"field":"year","message":"must be a whole number"}],
 "error":"validation failed"}
```

Validation rules: `title` (≤ 512 chars) and `author` (≤ 256 chars) must be
non-blank strings, surrounding whitespace is trimmed; `year`, when supplied,
must be a whole number in `[1, 2200]`; `isbn`, when supplied, must be a
non-blank string of at most 32 characters. `null` is accepted for the optional
fields and means "not set".

## Layout

```
src/json.{hpp,cpp}         JSON value type, parser, serializer
src/book.{hpp,cpp}         Book model, JSON mapping, input validation
src/store.{hpp,cpp}        SQLite persistence (prepared statements, mutex-guarded)
src/http_server.{hpp,cpp}  HTTP/1.1 server: parsing, routing, keep-alive
src/api.{hpp,cpp}          Route handlers mapping HTTP onto the store
src/main.cpp               CLI options, startup, signal-driven shutdown
tests/                     Test harness, HTTP client, and five test suites
```

## Design notes

- **Storage.** One SQLite connection guarded by a `std::mutex`, opened with a
  5 s busy timeout and WAL journalling for file-backed databases. All SQL uses
  bound parameters, so titles like `Robert'); DROP TABLE books;--` are stored
  verbatim (there is a test for this).
- **Concurrency.** One thread per connection, reaped as connections close.
  Idle keep-alive connections time out after 5 s, which also bounds how long a
  graceful shutdown can take.
- **Robustness.** Header blocks are capped at 16 KiB (`431`) and bodies at
  1 MiB (`413`); JSON nesting is capped at 64 levels; handler exceptions are
  turned into a `500` rather than terminating the process; `SIGPIPE` is ignored
  so a client disconnecting mid-response cannot kill the server. Connections
  are drained before closing, so a client that is still uploading a rejected
  body still receives the error response instead of a connection reset.
- **No external dependencies**, so the project builds offline anywhere a
  compiler and system SQLite are available. The suite is clean under
  AddressSanitizer, UndefinedBehaviorSanitizer, and ThreadSanitizer.

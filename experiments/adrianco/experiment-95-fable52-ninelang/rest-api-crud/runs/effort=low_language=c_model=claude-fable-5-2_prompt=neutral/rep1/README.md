# Book Collection REST API (C)

A small REST service for managing a book collection, written in C11 with POSIX
sockets and SQLite. No third-party dependencies beyond `libsqlite3`.

## Requirements

- A C11 compiler (`cc`, clang or gcc) and `make`
- SQLite 3 development library (`libsqlite3`)
  - macOS: ships with the Xcode command line tools
  - Debian/Ubuntu: `sudo apt-get install libsqlite3-dev`
- `curl` (only for the integration tests)

## Build and run

```sh
make            # builds ./bookapi
./bookapi       # listens on port 8080, stores data in ./books.db
```

Configuration is through environment variables:

| Variable  | Default    | Meaning                                         |
|-----------|------------|-------------------------------------------------|
| `PORT`    | `8080`     | TCP port to listen on                           |
| `DB_PATH` | `books.db` | SQLite database file (`:memory:` for ephemeral) |

```sh
PORT=9000 DB_PATH=/tmp/books.db ./bookapi
```

## Tests

```sh
make test
```

This runs:

- `tests/test_api.c` — unit tests of routing, validation, JSON handling and
  persistence against an in-memory SQLite database.
- `tests/integration.sh` — starts the real server and exercises every endpoint
  over HTTP with `curl`, including persistence across a restart. It uses port
  18765; override with `TEST_PORT`.

## API

All responses are JSON. Errors have the form `{"error": "message"}`.

| Method | Path          | Success          | Errors        |
|--------|---------------|------------------|---------------|
| GET    | `/health`     | 200              |               |
| POST   | `/books`      | 201, the book    | 400           |
| GET    | `/books`      | 200, array       |               |
| GET    | `/books/{id}` | 200, the book    | 404           |
| PUT    | `/books/{id}` | 200, the book    | 400, 404      |
| DELETE | `/books/{id}` | 204, no body     | 404           |

Unknown paths return 404, unsupported methods 405, and bodies over 1 MB 413.

### Book fields

| Field    | Type    | Rules                                        |
|----------|---------|----------------------------------------------|
| `id`     | integer | assigned by the server                       |
| `title`  | string  | required, must not be blank                  |
| `author` | string  | required, must not be blank                  |
| `year`   | integer | optional, 0–9999; `null` when not set        |
| `isbn`   | string  | optional; `null` when not set                |

`PUT` replaces the whole book: omitted optional fields become `null`.
Unknown fields in a request body are ignored.

`GET /books?author=NAME` returns only books whose author matches `NAME`
exactly (case-sensitive, URL-encoded).

### Examples

```sh
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
# 201 {"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}

curl 'localhost:8080/books?author=Frank%20Herbert'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
# 200 {"status":"ok"}
```

## Layout

```
src/main.c        entry point, configuration
src/server.c      minimal HTTP/1.1 server (single-threaded, one request per connection)
src/api.c         routing, handlers and SQLite access
src/book_json.c   JSON request parsing and validation
src/sb.c          growable string buffer and JSON string escaping
tests/            unit and integration tests
```

## Limitations

- The server handles one connection at a time and closes it after each
  response (no keep-alive, no chunked request bodies, no TLS). A slow client
  can hold up others for up to the 10-second I/O timeout.
- It listens on all interfaces and has no authentication.

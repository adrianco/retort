# Book Collection API (C)

A small REST API for managing a book collection. It is written in C, uses a
POSIX socket HTTP/1.1 server, and stores data in SQLite.

## Requirements

- A C compiler (`cc`/`gcc`/`clang`) with C11 support
- `make`
- SQLite 3 development headers and library
  - macOS: already available through the system SDK, or `brew install sqlite`
  - Debian/Ubuntu: `sudo apt install build-essential libsqlite3-dev`
  - Fedora: `sudo dnf install gcc make sqlite-devel`

## Build, run, test

```sh
make          # builds ./books
make test     # builds and runs the test suite (85 checks)
make run      # builds and starts the server on 127.0.0.1:8080
```

Configuration is through environment variables:

| Variable  | Default       | Meaning                         |
|-----------|---------------|---------------------------------|
| `PORT`    | `8080`        | TCP port to listen on           |
| `HOST`    | `127.0.0.1`   | Address to bind                 |
| `BOOKS_DB`| `books.db`    | Path to the SQLite database file |

```sh
PORT=3000 BOOKS_DB=/tmp/books.db ./books
```

The database schema is created automatically on first start.

## API

All responses are JSON. Errors have the form `{"error": "message"}`.

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

`year` and `isbn` are `null` when not set.

| Method | Path          | Description                                   | Success |
|--------|---------------|-----------------------------------------------|---------|
| POST   | `/books`      | Create a book                                 | `201` + book |
| GET    | `/books`      | List all books, ordered by id                 | `200` + array |
| GET    | `/books?author=NAME` | List books by author (case-insensitive exact match, URL-encoded) | `200` + array |
| GET    | `/books/{id}` | Get one book                                  | `200` + book |
| PUT    | `/books/{id}` | Replace a book's fields                       | `200` + book |
| DELETE | `/books/{id}` | Delete a book                                 | `204` (no body) |
| GET    | `/health`     | Health check                                  | `200` `{"status":"ok"}` |

### Fields and validation

- `title` (string, required): non-empty after trimming whitespace, at most 1000 bytes.
- `author` (string, required): same rules as `title`.
- `year` (integer, optional): between 0 and 9999 inclusive.
- `isbn` (string, optional): non-empty when present. Must be unique across books;
  a duplicate returns `409 Conflict`. Books without an ISBN do not conflict.

`PUT` is a full replacement: fields you leave out (`year`, `isbn`) are cleared.

### Status codes

| Code | When |
|------|------|
| 200  | Successful read or update |
| 201  | Book created |
| 204  | Book deleted |
| 400  | Invalid JSON, validation failure, or malformed id (`/books/abc`, `/books/0`) |
| 404  | Unknown book id or unknown route |
| 405  | Method not supported on that route |
| 409  | Duplicate ISBN |
| 413  | Request body over 1 MiB |
| 431  | Headers over 16 KiB |
| 501  | `Transfer-Encoding` (chunked) requests are not supported; send `Content-Length` |

## Examples

```sh
# Create
curl -i -X POST http://127.0.0.1:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# List, filtered by author
curl 'http://127.0.0.1:8080/books?author=Frank%20Herbert'

# Get, update, delete
curl http://127.0.0.1:8080/books/1
curl -X PUT http://127.0.0.1:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -i -X DELETE http://127.0.0.1:8080/books/1
```

## Project layout

```
src/
  util.c/h     allocation helpers and a growable string buffer
  json.c/h     JSON parser and string escaping
  store.c/h    SQLite persistence (books table)
  router.c/h   request routing, validation, and JSON responses (no sockets)
  http.c/h     HTTP/1.1 server over POSIX sockets
  main.c       entry point and configuration
tests/
  test_api.c   unit and integration tests (in-memory and on-disk SQLite)
Makefile
```

The router is independent of the socket layer, so the tests exercise the full
request-handling path against an in-memory database without opening a port.

## Limitations

- Single-threaded: connections are handled one at a time.
- One request per connection (`Connection: close`); no keep-alive.
- No authentication. The server binds to `127.0.0.1` by default; set `HOST`
  deliberately before exposing it on a network.

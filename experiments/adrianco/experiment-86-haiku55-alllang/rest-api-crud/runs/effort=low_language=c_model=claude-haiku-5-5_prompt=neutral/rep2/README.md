# Book Collection API (C)

A REST API for managing a book collection. It is written in C, stores data in
SQLite, and serves JSON over HTTP/1.1 using only POSIX sockets. The only
external dependency is SQLite.

## Requirements

- A C11 compiler (`cc`, `clang`, or `gcc`)
- `make`
- SQLite 3 development files. On macOS these come with the Command Line Tools
  (`xcode-select --install`). On Debian/Ubuntu: `sudo apt install libsqlite3-dev`.
  On Fedora: `sudo dnf install sqlite-devel`.

## Build, test, run

```sh
make            # builds build/bookapi
make test       # builds and runs build/test_all
PORT=8080 DB_PATH=books.db ./build/bookapi
```

Environment variables:

| Variable  | Default     | Meaning                                  |
|-----------|-------------|------------------------------------------|
| `PORT`    | `8080`      | TCP port to listen on (bound to 127.0.0.1) |
| `DB_PATH` | `books.db`  | SQLite database file (created if missing)  |

## Endpoints

| Method   | Path          | Success | Description                                  |
|----------|---------------|---------|----------------------------------------------|
| `POST`   | `/books`      | 201     | Create a book                                |
| `GET`    | `/books`      | 200     | List books; optional `?author=` filter       |
| `GET`    | `/books/{id}` | 200     | Get one book                                 |
| `PUT`    | `/books/{id}` | 200     | Replace a book (all fields)                  |
| `DELETE` | `/books/{id}` | 204     | Delete a book                                |
| `GET`    | `/health`     | 200     | Health check                                 |

Book body fields:

- `title` (string, required, non-blank, max 1000 chars)
- `author` (string, required, non-blank, max 1000 chars)
- `year` (integer 0–9999, optional, `null` if omitted)
- `isbn` (string, optional; ISBN-10 or ISBN-13 with optional hyphens, `X` allowed as the final ISBN-10 check digit)

Errors return JSON `{"error": "..."}` with an appropriate status:
`400` for invalid input, `404` for unknown routes or books, `405` for an
unsupported method on a known route, `413`/`431` for oversized requests,
and `500` for database failures.

### Examples

```sh
# Create
curl -i -X POST http://127.0.0.1:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-01359-3"}'

# List, and filter by author (case-insensitive exact match)
curl 'http://127.0.0.1:8080/books'
curl 'http://127.0.0.1:8080/books?author=Frank%20Herbert'

# Get, update, delete
curl http://127.0.0.1:8080/books/1
curl -X PUT http://127.0.0.1:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -i -X DELETE http://127.0.0.1:8080/books/1

# Health
curl http://127.0.0.1:8080/health
```

## Layout

```
src/
  main.c     entry point; reads PORT and DB_PATH
  http.c/.h  request parsing, query decoding, socket server
  api.c/.h   routing, validation, JSON responses (no sockets; unit-testable)
  db.c/.h    SQLite storage
  json.c/.h  minimal JSON object parser and string escaper
  strbuf.c/.h, util.c/.h  growable string buffer and allocation helpers
tests/
  test_all.c unit and integration tests
```

## Design notes and limitations

- The server handles one connection at a time (no threads). Each connection
  is closed after its response (`Connection: close`), so there is no keep-alive.
- Chunked request bodies (`Transfer-Encoding`) are rejected. Bodies are limited
  to 1 MiB and headers to 16 KiB.
- The server listens on 127.0.0.1 only. Put a reverse proxy in front of it if
  you need remote access, and add TLS and authentication there. The API itself
  has no authentication.
- ISBN validation checks format only, not the check digit.
- Tests in `tests/test_all.c` cover JSON parsing, request parsing, query
  decoding, validation, CRUD behaviour, routing errors, and a real socket
  round trip. They use an in-memory database.

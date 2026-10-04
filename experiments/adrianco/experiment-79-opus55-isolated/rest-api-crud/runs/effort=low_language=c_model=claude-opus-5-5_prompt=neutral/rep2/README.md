# Book Collection API

A small REST service for managing a book collection, written in C11 with no
framework: a POSIX-sockets HTTP server in front of SQLite.

## Requirements

- A C compiler (`cc`, clang or gcc) and `make`
- SQLite 3 development library (`libsqlite3`)
  - macOS: ships with the Xcode command line tools
  - Debian/Ubuntu: `apt install libsqlite3-dev`
- `curl` (only for the end-to-end test)

## Build and run

```sh
make            # builds ./bookapi
./bookapi       # listens on port 8080, stores data in ./books.db
```

Configuration is by environment variable:

| Variable  | Default    | Meaning                   |
|-----------|------------|---------------------------|
| `PORT`    | `8080`     | TCP port to listen on     |
| `DB_PATH` | `books.db` | SQLite database file path |

## Tests

```sh
make test
```

This runs `test_app` (handler-level tests against an in-memory database) and
`test_http.sh` (starts the real server on port 18734, override with
`TEST_PORT`, and drives it with curl).

## API

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

`title` and `author` are required non-blank strings. `year` (integer) and
`isbn` (string) are optional and are returned as `null` when absent.

| Method | Path          | Success          | Errors     |
|--------|---------------|------------------|------------|
| GET    | `/health`     | 200 `{"status":"ok"}` |       |
| POST   | `/books`      | 201, created book | 400       |
| GET    | `/books`      | 200, array of books; `?author=` filters by exact author | |
| GET    | `/books/{id}` | 200, book         | 404       |
| PUT    | `/books/{id}` | 200, updated book (full replacement) | 400, 404 |
| DELETE | `/books/{id}` | 204, no body      | 404       |

Errors are JSON: `{"error": "title is required"}`. Unknown paths return 404
and unsupported methods 405.

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:8080/books/1
```

## Layout

- `app.c` / `app.h` — JSON parsing, validation, SQLite access and routing
- `server.c` — HTTP server and `main`
- `test_app.c`, `test_http.sh` — tests

## Limitations

The server is single-threaded, handles one request per connection
(`Connection: close`), limits bodies to 1 MB and does not support chunked
request bodies.

# Books API (C + SQLite)

A small REST service for managing a book collection, written in plain C11 on
POSIX sockets with SQLite for storage. No dependencies beyond libc and
`libsqlite3`.

## Requirements

- A C compiler (`cc`, clang or gcc) and `make`
- SQLite development library
  - macOS: ships with the system (Xcode command line tools)
  - Debian/Ubuntu: `apt install libsqlite3-dev`
- `curl` (only for the end-to-end smoke test)

## Build and run

```sh
make            # builds ./books-api
./books-api     # listens on port 8080, stores data in ./books.db
```

Configuration is via environment variables:

| Variable   | Default    | Meaning                   |
|------------|------------|---------------------------|
| `PORT`     | `8080`     | TCP port to listen on     |
| `BOOKS_DB` | `books.db` | Path to the SQLite file   |

## Tests

```sh
make test
```

This runs `tests/test_api.c` (request-handler tests against an in-memory
database) and `tests/smoke.sh` (starts the real server and drives it with curl;
it uses port 18473, override with `TEST_PORT`).

## API

All bodies are JSON. A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

`title` and `author` are required non-empty strings. `year` (integer) and
`isbn` (string) are optional and are returned as `null` when unset.

| Method | Path                 | Success | Notes                                   |
|--------|----------------------|---------|-----------------------------------------|
| GET    | `/health`            | 200     | `{"status":"ok"}`                       |
| POST   | `/books`             | 201     | Returns the created book                |
| GET    | `/books`             | 200     | Array of books; `?author=` exact filter |
| GET    | `/books/{id}`        | 200     |                                         |
| PUT    | `/books/{id}`        | 200     | Full replacement; returns updated book  |
| DELETE | `/books/{id}`        | 204     | Empty body                              |

Errors return `{"error": "..."}` with `400` (invalid JSON or failed
validation), `404` (unknown book or route), `405` (unsupported method) or
`413` (body over 1 MB).

### Examples

```sh
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl localhost:8080/books
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"F. Herbert"}'
curl -X DELETE localhost:8080/books/1
```

## Limitations

- Requests are handled one at a time on a single thread, with one request per
  connection (`Connection: close`) and a 5 second socket timeout.
- The JSON parser accepts a flat object only; nested arrays/objects are
  rejected with `400`.
- `PUT` replaces the whole record, so omitted optional fields become `null`.

## Layout

- `src/api.c`, `src/api.h` — routing, validation, JSON, SQLite access
- `src/main.c` — HTTP server
- `tests/` — tests

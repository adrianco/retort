# Books API (Objective-C)

A small REST service for managing a book collection, written in Objective-C with
Foundation, BSD sockets and SQLite. No third-party dependencies.

## Requirements

- macOS with the Xcode Command Line Tools (`clang`, `make`; `libsqlite3` ships with the OS)

## Build, run, test

```sh
make            # builds build/books-api
make run        # builds and starts the server
make test       # builds and runs the test suite
make clean
```

Configuration is via environment variables:

| Variable  | Default     | Meaning                                      |
|-----------|-------------|----------------------------------------------|
| `PORT`    | `8080`      | Listening port                               |
| `HOST`    | `127.0.0.1` | IPv4 address to bind (`0.0.0.0` for all)     |
| `DB_PATH` | `books.db`  | SQLite database file (created if missing)    |

```sh
PORT=9000 DB_PATH=/tmp/books.db ./build/books-api
```

## API

All responses are JSON. A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

| Method | Path          | Success          | Errors                  |
|--------|---------------|------------------|-------------------------|
| GET    | `/health`     | 200 `{"status":"ok"}` |                    |
| POST   | `/books`      | 201 + book, `Location` header | 400        |
| GET    | `/books`      | 200 + array; `?author=` filters by exact, case-insensitive author | |
| GET    | `/books/{id}` | 200 + book       | 404                     |
| PUT    | `/books/{id}` | 200 + book       | 400, 404                |
| DELETE | `/books/{id}` | 204 (empty body) | 404                     |

Validation (POST and PUT): `title` and `author` are required non-blank strings;
`year` (integer) and `isbn` (string) are optional and stored as `null` when omitted.
PUT replaces the whole record. Failures return 400:

```json
{"error": "validation failed", "details": ["title is required"]}
```

Other errors use `{"error": "..."}`: 404 for unknown paths/ids, 405 (with `Allow`)
for unsupported methods, 413 for bodies over 1 MB.

### Example

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune Messiah","author":"Frank Herbert"}'
curl -X DELETE localhost:8080/books/1
```

## Layout

- `src/BookStore.{h,m}` – SQLite persistence (prepared statements)
- `src/BookAPI.{h,m}` – routing, validation, JSON responses (transport-independent)
- `src/HTTPServer.{h,m}` – minimal HTTP/1.1 server (one request per connection)
- `src/main.m` – entry point
- `tests/BookTests.m` – self-contained test runner: API tests against an in-memory
  database plus an end-to-end test over a real socket

## Limitations

The HTTP server is intentionally minimal: no keep-alive, chunked request bodies or TLS.

# Book Collection REST API (C++17)

A small REST service for managing books, backed by SQLite.

It has no third-party dependencies beyond SQLite itself: the HTTP server
(POSIX sockets, one thread per connection) and JSON handling are implemented
in `src/`.

## Requirements

- A C++17 compiler (clang or gcc) on macOS or Linux
- CMake 3.16+
- SQLite3 development files (bundled with macOS; `apt install libsqlite3-dev` on Debian/Ubuntu)

## Build

```sh
cmake -S . -B build
cmake --build build
```

## Run

```sh
./build/book_api
```

Configuration is via environment variables:

| Variable  | Default     | Meaning                                  |
|-----------|-------------|------------------------------------------|
| `PORT`    | `8080`      | TCP port (`0` picks a free port)         |
| `HOST`    | `127.0.0.1` | IPv4 address to bind (`0.0.0.0` for all) |
| `DB_PATH` | `books.db`  | SQLite database file                     |

## Test

```sh
ctest --test-dir build --output-on-failure   # or: ./build/book_tests
```

The tests (`tests/test_main.cpp`) cover the handlers against an in-memory
database, persistence to a file, and an end-to-end run over a real TCP socket.

## API

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

`title` and `author` are required non-blank strings. `year` (integer) and
`isbn` (string) are optional and are returned as `null` when absent.

| Method | Path          | Success          | Errors                                |
|--------|---------------|------------------|---------------------------------------|
| GET    | `/health`     | 200 `{"status":"ok"}` |                                  |
| POST   | `/books`      | 201 + book       | 400 invalid JSON / validation failure |
| GET    | `/books`      | 200 + array      |                                       |
| GET    | `/books?author=NAME` | 200 + array (exact author match) |                |
| GET    | `/books/{id}` | 200 + book       | 404                                   |
| PUT    | `/books/{id}` | 200 + book       | 400, 404                              |
| DELETE | `/books/{id}` | 204 (no body)    | 404                                   |

`PUT` replaces the whole book, so omitted optional fields become `null`.
Errors are JSON: `{"error": "title is required"}`. Unknown paths return 404
and unsupported methods on known paths return 405.

### Examples

```sh
curl -i -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl -i 'localhost:8080/books?author=Frank%20Herbert'
curl -i localhost:8080/books/1
curl -i -X PUT localhost:8080/books/1 -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -i -X DELETE localhost:8080/books/1
```

## Limitations

- Each connection serves one request (`Connection: close`); no keep-alive, TLS or chunked request bodies.
- Request bodies are limited to 1 MB.

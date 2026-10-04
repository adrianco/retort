# Book Collection REST API (C++)

A small REST service for managing a book collection, written in C++17 and
backed by SQLite.

No web framework was specified, so the service has no third-party
dependencies beyond SQLite itself: the HTTP server (POSIX sockets) and JSON
handling are implemented in `src/`.

## Requirements

- A C++17 compiler (clang or gcc) on macOS or Linux
- CMake 3.14+
- SQLite3 development files (bundled with macOS; `apt install libsqlite3-dev`
  on Debian/Ubuntu)

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

| Variable  | Default     | Meaning                                       |
|-----------|-------------|-----------------------------------------------|
| `PORT`    | `8080`      | TCP port to listen on                         |
| `HOST`    | `127.0.0.1` | IPv4 address to bind (`0.0.0.0` for all)      |
| `DB_PATH` | `books.db`  | SQLite database file (`:memory:` for no file) |

Stop the server with Ctrl-C or `SIGTERM`; in-flight requests finish first.

## Test

```sh
ctest --test-dir build --output-on-failure
```

The tests (`tests/test_main.cpp`) cover each endpoint against an in-memory
database, validation, persistence to a file, and an end-to-end run over a real
TCP socket.

## API

All responses are JSON. Errors have the form `{"error": "message"}`.

| Method | Path          | Success          | Errors     |
|--------|---------------|------------------|------------|
| GET    | `/health`     | 200              |            |
| POST   | `/books`      | 201, the book    | 400        |
| GET    | `/books`      | 200, array       |            |
| GET    | `/books/{id}` | 200, the book    | 404        |
| PUT    | `/books/{id}` | 200, the book    | 400, 404   |
| DELETE | `/books/{id}` | 204, empty body  | 404        |

Unknown paths return 404 and unsupported methods return 405.

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

- `title` and `author` are required and must be non-blank strings.
- `year` (integer) and `isbn` (string) are optional and are `null` when absent.
- `PUT` replaces the whole book, so it needs `title` and `author` too, and
  omitted optional fields become `null`.
- `GET /books?author=Frank%20Herbert` returns only that author's books. The
  match is on the full name and ignores ASCII case.

### Examples

```sh
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl localhost:8080/books
curl 'localhost:8080/books?author=Frank%20Herbert'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

## Limits

- One request per connection (`Connection: close`); no keep-alive, TLS or
  chunked request bodies.
- Request bodies are capped at 1 MB and headers at 16 KB.

## Layout

```
src/main.cpp         entry point, configuration, signal handling
src/app.*            routing, validation, JSON responses
src/store.*          SQLite persistence
src/http_server.*    HTTP/1.1 server
src/json.hpp         JSON parser and string escaping
tests/test_main.cpp  tests
```

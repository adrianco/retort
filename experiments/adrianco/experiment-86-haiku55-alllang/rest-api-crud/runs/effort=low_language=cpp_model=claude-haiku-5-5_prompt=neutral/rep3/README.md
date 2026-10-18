# Book Collection API (C++)

A REST service for managing a book collection. Data is stored in SQLite; the
HTTP server and JSON handling are built in, so there are no third-party
dependencies beyond SQLite.

## Requirements

- C++17 compiler (clang++ or g++)
- CMake 3.16+
- SQLite 3 development files (`libsqlite3` headers and library)
  - macOS: ships with the SDK, or `brew install sqlite`
  - Debian/Ubuntu: `sudo apt install libsqlite3-dev`

## Build

```sh
cmake -S . -B build
cmake --build build
```

## Run

```sh
./build/book_server
```

Environment variables:

| Variable   | Default        | Meaning                        |
|------------|----------------|--------------------------------|
| `PORT`     | `8080`         | Port to listen on              |
| `HOST`     | `127.0.0.1`    | IPv4 address to bind           |
| `BOOKS_DB` | `books.db`     | SQLite database file           |

Example:

```sh
PORT=8080 BOOKS_DB=./books.db ./build/book_server
```

## Test

```sh
cmake --build build && ./build/book_tests
# or
ctest --test-dir build --output-on-failure
```

## API

Bodies and responses are JSON. Errors are `{"error": "<message>"}`.

A book has the shape:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

`year` and `isbn` are optional and are `null` when absent. `title` and `author`
are required and must be non-empty after trimming whitespace. `year`, when given,
must be an integer between -10000 and 10000. `isbn`, when given, must be a non-empty string.

| Method | Path          | Description                                              | Success               |
|--------|---------------|----------------------------------------------------------|-----------------------|
| POST   | `/books`      | Create a book from `title`, `author`, `year`, `isbn`     | `201` + `Location`    |
| GET    | `/books`      | List books; optional `?author=` (case-insensitive exact) | `200`                 |
| GET    | `/books/{id}` | Get one book                                             | `200`                 |
| PUT    | `/books/{id}` | Replace a book (full update, same validation as POST)    | `200`                 |
| DELETE | `/books/{id}` | Delete a book                                            | `204` (no body)       |
| GET    | `/health`     | Health check                                             | `200` `{"status":"ok"}` |

Error statuses:

- `400` – malformed JSON, body not an object, or failed validation
- `404` – unknown book id or unknown route
- `405` – known path with an unsupported method (includes `Allow` header)
- `413` – body larger than 1 MiB
- `501` – `Transfer-Encoding` requests are not supported

### Examples

```sh
curl -i -X POST http://127.0.0.1:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl 'http://127.0.0.1:8080/books?author=Frank%20Herbert'
curl http://127.0.0.1:8080/books/1
curl -X PUT http://127.0.0.1:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -i -X DELETE http://127.0.0.1:8080/books/1
curl http://127.0.0.1:8080/health
```

## Layout

```
include/bookapi/   public headers (json, book, repository, api, http_server)
src/               implementations and main.cpp
tests/             dependency-free test harness and tests
```

## Design notes

- `BookApi` is transport-independent: it maps a `Request` to a `Response`, so
  it is tested directly without sockets.
- `HttpServer` is a small blocking HTTP/1.1 server that handles one request
  per connection, sequentially. It is suited to a local or single-user service,
  not high-concurrency traffic.
- `BookRepository` uses a single SQLite connection and is not thread-safe.
- Author filtering uses SQLite `COLLATE NOCASE` on the full author string.

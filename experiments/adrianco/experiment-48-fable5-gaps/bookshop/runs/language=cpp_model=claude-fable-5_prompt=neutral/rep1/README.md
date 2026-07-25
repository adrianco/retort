# Book Collection REST API (C++)

A small REST service for managing a book collection, written in C++17 with
[cpp-httplib](https://github.com/yhirose/cpp-httplib) (HTTP server),
[nlohmann/json](https://github.com/nlohmann/json) (JSON), and SQLite for storage.
Both header-only libraries are vendored in `third_party/`, so the only external
dependencies are a C++17 compiler, CMake ≥ 3.16, and the SQLite3 library
(preinstalled on macOS; `libsqlite3-dev` on Debian/Ubuntu).

## Build

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
```

## Run

```sh
./build/book_api                # listens on port 8080, database file books.db
./build/book_api 9000 mydb.db   # custom port and database path
PORT=9000 BOOKS_DB=mydb.db ./build/book_api   # same, via environment variables
```

## Test

```sh
cd build && ctest --output-on-failure
```

The test binary (`build/book_tests`) starts the real server on an ephemeral port
with an in-memory SQLite database and exercises every endpoint over HTTP:
health check, create/get round-trip, optional-field defaults, input validation
(missing/empty title or author, malformed JSON, wrong types), listing with the
author filter, update, delete, and 404 handling.

## API

| Method | Path              | Description                          | Success |
|--------|-------------------|--------------------------------------|---------|
| GET    | `/health`         | Health check                         | 200     |
| POST   | `/books`          | Create a book                        | 201     |
| GET    | `/books`          | List books (`?author=` filter)       | 200     |
| GET    | `/books/{id}`     | Get one book                         | 200     |
| PUT    | `/books/{id}`     | Update a book (full replacement)     | 200     |
| DELETE | `/books/{id}`     | Delete a book                        | 204     |

A book is `{"id": 1, "title": "...", "author": "...", "year": 1975, "isbn": "..."}`.
`title` and `author` are required non-empty strings; `year` (integer) and `isbn`
(string) are optional and returned as `null` when unset. Validation failures and
malformed JSON return `400`, unknown IDs return `404`, and errors have the shape
`{"error": "message"}`.

### Examples

```sh
curl -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'

curl 'localhost:8080/books?author=Frank%20Herbert'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'
curl -X DELETE localhost:8080/books/1
```

## Layout

- `src/book_store.{h,cpp}` — SQLite-backed store (schema creation, CRUD, thread-safe)
- `src/api.{h,cpp}` — route registration, JSON serialization, input validation
- `src/main.cpp` — entry point / configuration
- `tests/test_api.cpp` — HTTP integration tests
- `third_party/` — vendored httplib.h (v0.18.3) and json.hpp (v3.11.3)

# Book Collection API (C++)

A small REST API for managing a book collection, written in C++17. It uses
[cpp-httplib](https://github.com/yhirose/cpp-httplib) for the HTTP server,
[nlohmann/json](https://github.com/nlohmann/json) for JSON, and **SQLite** for
storage. Both header-only libraries are vendored under `third_party/`, so the
only external dependency is SQLite (present on macOS and most Linux distros).

## Endpoints

| Method | Path           | Description                                  | Success |
|--------|----------------|----------------------------------------------|---------|
| GET    | `/health`      | Health check                                 | 200     |
| POST   | `/books`       | Create a book                                | 201     |
| GET    | `/books`       | List books; optional `?author=` filter       | 200     |
| GET    | `/books/{id}`  | Fetch one book                               | 200     |
| PUT    | `/books/{id}`  | Replace a book                               | 200     |
| DELETE | `/books/{id}`  | Delete a book                                | 204     |

A book has the fields `title`, `author` (both **required**), `year` and `isbn`
(both optional). `id` is assigned by the server.

### Status codes

- `200` / `201` / `204` — success
- `400` — invalid input (missing/blank `title` or `author`, malformed JSON, bad id)
- `404` — no book with the given id
- `500` — unexpected server/database error

Error responses have the shape `{"error": "message"}`.

## Requirements

- A C++17 compiler (clang or gcc)
- CMake ≥ 3.16
- SQLite3 development headers/library
  - macOS: included with the Command Line Tools / Xcode SDK
  - Debian/Ubuntu: `sudo apt-get install libsqlite3-dev`

## Build

```sh
cmake -S . -B build
cmake --build build
```

This produces two binaries in `build/`:

- `book_api` — the server
- `book_tests` — the test suite

## Run

```sh
./build/book_api
```

The server listens on `0.0.0.0:8080` and stores data in `books.db` by default.
Configuration (in order of increasing precedence):

- `BOOKS_DB` / `PORT` environment variables
- positional args: `./build/book_api <db_path> <port>`

Example:

```sh
PORT=9000 BOOKS_DB=/tmp/books.db ./build/book_api
# or
./build/book_api /tmp/books.db 9000
```

## Example requests

```sh
# Health
curl localhost:8080/health

# Create
curl -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"9780441172719"}'

# List (optionally filtered by author)
curl localhost:8080/books
curl 'localhost:8080/books?author=Herbert'

# Get one
curl localhost:8080/books/1

# Update
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Revised)","author":"Herbert","year":1965}'

# Delete
curl -X DELETE localhost:8080/books/1
```

## Tests

```sh
./build/book_tests
# or via ctest
ctest --test-dir build --output-on-failure
```

The suite exercises the store and handler layer against an in-memory SQLite
database (create/get, validation, author filtering, update, delete, optional
fields) and runs a full HTTP round-trip against a live server instance.

## Project layout

```
src/
  book.h          # Book model + JSON serialization
  book_store.{h,cpp}  # SQLite persistence layer
  handlers.{h,cpp}    # Request parsing + endpoint logic (transport-agnostic)
  main.cpp        # httplib server wiring
tests/
  test_main.cpp   # test suite
third_party/      # vendored httplib + nlohmann/json headers
CMakeLists.txt
```

The handler logic is kept independent of httplib so it can be unit-tested
directly without spinning up a network server.

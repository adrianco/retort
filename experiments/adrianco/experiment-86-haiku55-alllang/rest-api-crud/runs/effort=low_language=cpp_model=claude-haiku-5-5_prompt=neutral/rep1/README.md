# Books API (C++)

A REST API for managing a book collection. Built with Boost.Beast (HTTP),
Boost.JSON (serialization) and SQLite (storage).

## Prerequisites

- CMake 3.20+
- A C++17 compiler (clang++ or g++)
- Boost 1.84+ with the `json` and `unit_test_framework` components
- SQLite 3 development headers and library

On macOS with Homebrew:

```sh
brew install cmake boost sqlite
```

On Debian/Ubuntu:

```sh
sudo apt install cmake libboost-all-dev libsqlite3-dev
```

## Build

```sh
cmake -S . -B build
cmake --build build
```

## Run

```sh
./build/books_server [port] [database-path]
```

Defaults: port `8080`, database `books.db` in the working directory. The
database and schema are created on first start. The server listens on
`127.0.0.1` and handles one connection at a time.

## Test

```sh
ctest --test-dir build --output-on-failure
```

Or run the test binary directly: `./build/books_tests`.

## API

All responses are JSON. Errors have the form `{"error": "message"}`.

A book looks like:

```json
{"id": 1, "title": "1984", "author": "George Orwell", "year": 1949, "isbn": "9780451524935"}
```

`year` and `isbn` may be `null`.

| Method | Path          | Description                                  | Success |
|--------|---------------|----------------------------------------------|---------|
| POST   | `/books`      | Create a book                                | 201     |
| GET    | `/books`      | List books; optional `?author=` exact match  | 200     |
| GET    | `/books/{id}` | Get one book                                 | 200     |
| PUT    | `/books/{id}` | Replace a book's fields                      | 200     |
| DELETE | `/books/{id}` | Delete a book                                | 204     |
| GET    | `/health`     | Liveness and database check                  | 200     |

### Fields

| Field    | Type    | Required | Rules                                            |
|----------|---------|----------|--------------------------------------------------|
| `title`  | string  | yes      | Non-empty after trimming whitespace              |
| `author` | string  | yes      | Non-empty after trimming whitespace              |
| `year`   | integer | no       | 1 to 9999                                        |
| `isbn`   | string  | no       | ISBN-10 or ISBN-13; hyphens and spaces allowed; stored without them; unique |

`PUT` is a full replacement: fields you omit are cleared to `null`. Send the
complete book.

### Status codes

- `400` invalid JSON, missing or invalid field
- `404` unknown route, or no book with that id
- `405` method not allowed on that path
- `409` ISBN already used by another book
- `500` unexpected server error (details are logged, not returned)

## Examples

```sh
# Create
curl -i -X POST http://127.0.0.1:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0-45-152493-5"}'

# List, filtered by author (URL-encode spaces)
curl 'http://127.0.0.1:8080/books?author=George%20Orwell'

# Get, update, delete
curl http://127.0.0.1:8080/books/1
curl -X PUT http://127.0.0.1:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949}'
curl -i -X DELETE http://127.0.0.1:8080/books/1

# Health
curl http://127.0.0.1:8080/health
```

## Layout

```
src/book.{hpp,cpp}        Book model, input validation, JSON conversion
src/repository.{hpp,cpp}  SQLite storage
src/api.{hpp,cpp}         Routing and request handling (no sockets)
src/main.cpp              HTTP server (Boost.Beast)
tests/api_tests.cpp       Tests against an in-memory database
```

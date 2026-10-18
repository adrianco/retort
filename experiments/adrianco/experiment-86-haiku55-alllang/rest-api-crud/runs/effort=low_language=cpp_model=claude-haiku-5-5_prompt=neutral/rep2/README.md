# Book API

A REST service for managing a book collection, written in C++17. Books are stored in SQLite.

- HTTP: [cpp-httplib](https://github.com/yhirose/cpp-httplib) (fetched by CMake)
- JSON: [nlohmann/json](https://github.com/nlohmann/json) (fetched by CMake)
- Storage: SQLite 3 (system library)

## Requirements

- CMake 3.16+
- A C++17 compiler (Clang or GCC)
- SQLite 3 development headers and library. On macOS the Xcode SDK provides them. On Debian/Ubuntu, install `libsqlite3-dev`.
- Git and network access the first time you configure (CMake downloads the dependencies)

## Build

```sh
cmake -S . -B build
cmake --build build
```

## Run

```sh
./build/book_api
```

The server listens on `http://127.0.0.1:8080` by default. Two environment variables change this:

| Variable  | Default     | Purpose                              |
|-----------|-------------|--------------------------------------|
| `PORT`    | `8080`      | TCP port to listen on                |
| `DB_PATH` | `books.db`  | SQLite database file (created if missing) |

The server binds to localhost only, because it has no authentication.

## Test

```sh
ctest --test-dir build --output-on-failure
# or run the test binary directly:
./build/book_api_tests
```

The suite contains repository tests, validation tests, and HTTP integration tests that start a server on an ephemeral port.

## API

Every response is JSON. A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

`year` and `isbn` may be `null`.

| Method | Path          | Description                                    | Success          |
|--------|---------------|------------------------------------------------|------------------|
| POST   | `/books`      | Create a book                                  | `201` + book, `Location` header |
| GET    | `/books`      | List books; optional `?author=` exact match    | `200` + array    |
| GET    | `/books/{id}` | Get one book                                   | `200` + book     |
| PUT    | `/books/{id}` | Replace a book's fields (full update)          | `200` + book     |
| DELETE | `/books/{id}` | Delete a book                                  | `204`, no body   |
| GET    | `/health`     | Health check                                   | `200` `{"status":"ok"}` |

### Fields

| Field    | Type    | Required | Rules                            |
|----------|---------|----------|----------------------------------|
| `title`  | string  | yes      | non-blank                        |
| `author` | string  | yes      | non-blank                        |
| `year`   | integer | no       | 0–9999                           |
| `isbn`   | string  | no       | any string                       |

`PUT` takes the same body as `POST`. It replaces all fields, so omitted optional fields are cleared.

### Errors

Error responses use the shape `{"error": "...", "details": [...]}`. `details` appears only for validation failures and lists every problem found.

| Status | Cause                                              |
|--------|----------------------------------------------------|
| 400    | Invalid JSON, failed validation, or a non-numeric/non-positive id |
| 404    | No book with that id                               |
| 500    | Unexpected server error                            |

### Examples

```sh
curl -i -X POST http://127.0.0.1:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl http://127.0.0.1:8080/books?author=Frank%20Herbert
curl -X PUT http://127.0.0.1:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert"}'
curl -X DELETE http://127.0.0.1:8080/books/1
curl http://127.0.0.1:8080/health
```

## Project layout

```
CMakeLists.txt
src/
  database.{h,cpp}    SQLite repository (BookRepository)
  validation.{h,cpp}  Request body validation
  api.{h,cpp}         HTTP routes
  main.cpp            Entry point
tests/
  test_books.cpp      Unit and integration tests
```

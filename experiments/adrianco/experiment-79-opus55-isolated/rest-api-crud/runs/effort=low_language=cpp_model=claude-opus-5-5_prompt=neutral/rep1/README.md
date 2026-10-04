# Books API

A REST service for managing a book collection, written in C++17 and backed by SQLite.

It has no third-party dependencies beyond SQLite itself: the HTTP server
(POSIX sockets), JSON parsing and the test runner are all in this repository.

## Requirements

- A C++17 compiler (clang or gcc) on macOS or Linux
- CMake 3.14+
- SQLite3 development files (bundled with macOS; `apt install libsqlite3-dev` on Debian/Ubuntu)

## Build

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

## Run

```sh
./build/books_api
```

Configuration is by environment variable:

| Variable  | Default     | Meaning                                   |
|-----------|-------------|-------------------------------------------|
| `HOST`    | `127.0.0.1` | IPv4 address to listen on (`0.0.0.0` for all interfaces) |
| `PORT`    | `8080`      | TCP port                                  |
| `DB_PATH` | `books.db`  | SQLite database file (created if missing) |

Stop the server with Ctrl-C.

## Test

```sh
ctest --test-dir build --output-on-failure
```

The tests (`tests/tests.cpp`) exercise the handlers against an in-memory
database, check persistence across a database reopen, and run an end-to-end
pass over a real socket.

## API

A book looks like this; `year` and `isbn` are optional and are `null` when unset:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

| Method | Path          | Success          | Errors     |
|--------|---------------|------------------|------------|
| GET    | `/health`     | 200 `{"status":"ok"}` |       |
| POST   | `/books`      | 201, the new book | 400       |
| GET    | `/books`      | 200, array of books, ordered by id |  |
| GET    | `/books/{id}` | 200, the book    | 404        |
| PUT    | `/books/{id}` | 200, the updated book | 400, 404 |
| DELETE | `/books/{id}` | 204, no body     | 404        |

- `GET /books?author=Name` returns only books whose author matches exactly (case-sensitive).
- `PUT` replaces the whole record, so `title` and `author` are required and
  omitted optional fields become `null`.
- Validation: `title` and `author` must be non-blank strings, `year` an
  integer, `isbn` a string. Failures return 400.
- Errors are JSON: `{"error": "title is required"}`. Unsupported methods get
  405, oversized bodies (over 1 MB) 413.

### Example

```sh
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune Messiah","author":"Frank Herbert"}'
curl -X DELETE localhost:8080/books/1
```

## Layout

- `src/app.*` — routing, validation and handlers (transport-independent)
- `src/store.*` — SQLite persistence
- `src/server.*` — HTTP/1.1 server (one thread per connection, `Connection: close`)
- `src/json.*` — JSON parser and string escaping
- `src/main.cpp` — entry point

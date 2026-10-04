# Books API (C++)

A small REST service for managing a book collection, written in C++17 with
SQLite for storage. It has no third-party dependencies beyond SQLite: the HTTP
server (POSIX sockets) and JSON handling are implemented in `src/`.

## Requirements

- A C++17 compiler (clang or gcc) on macOS or Linux
- CMake 3.14+
- SQLite3 development files (bundled with macOS; `apt install libsqlite3-dev` on Debian/Ubuntu)

## Build

```sh
cmake -S . -B build
cmake --build build
```

## Run

```sh
./build/books_server
```

Configuration is via environment variables:

| Variable  | Default     | Meaning                                   |
|-----------|-------------|-------------------------------------------|
| `PORT`    | `8080`      | Port to listen on                         |
| `HOST`    | `127.0.0.1` | IPv4 address to bind (`0.0.0.0` for all)  |
| `DB_PATH` | `books.db`  | SQLite database file (created if missing) |

## Test

```sh
cd build && ctest --output-on-failure
```

The tests (`tests/test_api.cpp`) exercise the request handler against an
in-memory database and also run the real server on an ephemeral port.

## API

All request and response bodies are JSON.

| Method | Path          | Success          | Errors     |
|--------|---------------|------------------|------------|
| GET    | `/health`     | 200 `{"status":"ok"}` |       |
| POST   | `/books`      | 201, created book | 400       |
| GET    | `/books`      | 200, array of books (`?author=` exact-match filter) | |
| GET    | `/books/{id}` | 200, book        | 404        |
| PUT    | `/books/{id}` | 200, updated book | 400, 404  |
| DELETE | `/books/{id}` | 204, no body     | 404        |

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

Validation: `title` and `author` are required, non-blank strings. `year`
(integer) and `isbn` (string) are optional and returned as `null` when absent.
`PUT` replaces the whole book, so omitted optional fields become `null`.
Errors are returned as `{"error": "message"}`; unsupported methods get 405.

### Example

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank+Herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:8080/books/1
```

## Layout

- `src/api.*` – routing, validation, JSON responses (transport independent)
- `src/store.*` – SQLite persistence
- `src/http_server.*` – minimal HTTP/1.1 server (thread per connection, `Connection: close`)
- `src/json.*` – JSON parser and string escaping
- `src/main.cpp` – entry point

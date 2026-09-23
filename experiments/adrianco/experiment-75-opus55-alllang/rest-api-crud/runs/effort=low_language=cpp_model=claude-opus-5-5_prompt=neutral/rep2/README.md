# Book Collection REST API (C++17 + SQLite)

A small REST service for managing books. It has no dependencies apart from SQLite3. The HTTP server is a minimal built-in POSIX socket server, and the JSON handling is hand-written.

## Build & test

```sh
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure   # or ./build/books_tests
```

You need a C++17 compiler, CMake ≥ 3.16 and the SQLite3 development headers (on Debian/Ubuntu: `apt install libsqlite3-dev`; on macOS they come with the SDK).

## Run

```sh
./build/books_server [port=8080] [db_path=books.db]
```

## Endpoints

| Method | Path | Success | Errors |
|---|---|---|---|
| GET | /health | 200 `{"status":"ok"}` | |
| POST | /books | 201 book | 400 validation |
| GET | /books[?author=Name] | 200 array | |
| GET | /books/{id} | 200 book | 404 |
| PUT | /books/{id} | 200 book | 400, 404 |
| DELETE | /books/{id} | 204 | 404 |

Book JSON: `{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}`.
`title` and `author` must be non-empty strings. `year` is optional and must be an integer from 0 to 9999. `isbn` is optional and must be a string. PUT replaces the whole record. The `author` filter is an exact match. Errors return `{"error":"..."}`.

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl "localhost:8080/books?author=Frank%20Herbert"
```

## Layout

- `api.hpp/.cpp`: routing, validation, JSON and SQLite storage (`BookApi::handle(Request) -> Response`)
- `main.cpp`: HTTP server
- `tests.cpp`: tests against an in-memory database

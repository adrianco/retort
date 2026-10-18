# Book Collection REST API

A small C++17 REST service that stores books in SQLite. The service provides JSON endpoints for creating, listing, retrieving, updating, and deleting books, plus a health check.

## Requirements

- CMake 3.16 or newer
- A C++17 compiler
- SQLite 3 development headers and library

The HTTP server uses POSIX sockets, so this implementation is intended for macOS and Linux.

## Build and test

```sh
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

## Run

```sh
./build/book_server
```

The server listens on port `8080` and stores data in `books.db` in the current directory. Set `PORT` and `BOOKS_DB` to override these defaults.

## API

- `GET /health` — returns `{"status":"ok"}`.
- `POST /books` — create a book. `title` and `author` are required non-empty strings; `year` is an optional integer from 0 through 9999, and `isbn` is an optional string.
- `GET /books` — list all books. Filter with `?author=Exact%20Author`.
- `GET /books/{id}` — fetch a book by ID.
- `PUT /books/{id}` — replace a book's fields using the same JSON format as creation.
- `DELETE /books/{id}` — delete a book.

Book responses have the form `{"id":1,"title":"...","author":"...","year":2024,"isbn":"..."}`. Create returns `201`, reads and updates return `200`, deletes return `204`, invalid input returns `400`, and missing resources return `404`.

Example:

```sh
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The C++ Book","author":"Ada Lovelace","year":2024,"isbn":"123"}'
curl 'http://localhost:8080/books?author=Ada%20Lovelace'
```

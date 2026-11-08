# Book collection API

A C++17 HTTP service using libmicrohttpd, json-c, and SQLite. Data is persisted in a local SQLite database.

## Build and run

Install a C++17 compiler, CMake, pkg-config, SQLite development headers, libmicrohttpd, and json-c. For example, on macOS with Homebrew: `brew install cmake pkg-config sqlite libmicrohttpd json-c`. On Debian/Ubuntu: `sudo apt install build-essential cmake pkg-config libsqlite3-dev libmicrohttpd-dev libjson-c-dev`.

```sh
cmake -S . -B build
cmake --build build
./build/book_service                 # port 8080, database ./books.db
./build/book_service 8081 mybooks.db # optional port and database path
```

Stop the server with Ctrl+C. Run the integration tests (requires Python 3) with `ctest --test-dir build --output-on-failure`.

## API

All responses are JSON. A book has `id`, `title`, `author`, `year`, and `isbn`. `title` and `author` must be non-blank strings. `year` is an integer or null; `isbn` is a string or null. Both optional fields default to null. PUT replaces all book fields and requires title and author. The author filter is an exact, case-sensitive match.

- `GET /health` returns `{"status":"ok"}`.
- `POST /books` creates a book and returns it with status 201.
- `GET /books` returns an array; `GET /books?author=...` filters it.
- `GET /books/{id}` returns one book.
- `PUT /books/{id}` replaces a book and returns it.
- `DELETE /books/{id}` removes a book and returns `{"deleted":true}`.

Invalid input returns 400, an unknown route or book returns 404, unsupported methods return 405, and database errors return 500. Errors have the form `{"error":"..."}`. Request bodies are limited to 1 MiB.

```sh
curl -X POST http://localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'http://localhost:8080/books?author=Frank%20Herbert'
```

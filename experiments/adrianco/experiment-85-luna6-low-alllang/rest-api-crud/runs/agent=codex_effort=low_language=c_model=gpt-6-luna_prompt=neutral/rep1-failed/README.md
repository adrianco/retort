# Book Collection API

A small C REST service backed by SQLite. It uses libmicrohttpd for HTTP handling and SQLite for persistent storage.

## Requirements

- A C compiler
- SQLite development headers and library
- libmicrohttpd development headers and library
- `pkg-config` and Python 3 (for tests)

On macOS with Homebrew, install dependencies with `brew install sqlite libmicrohttpd pkg-config`. On Debian or Ubuntu, use `sudo apt install build-essential pkg-config libsqlite3-dev libmicrohttpd-dev`.

## Build and run

```sh
make
./book_service                 # listens on port 8080
./book_service 9000            # choose another port
```

The database defaults to `books.db` in the current directory. Set `BOOKS_DB=/path/to/file.db` to choose another SQLite file.

## API

- `GET /health` — `{"status":"ok"}`
- `POST /books` — JSON object with required `title` and `author`; optional `year` and `isbn`. Returns the created book with status 201.
- `GET /books` — list books; optional `?author=...` filter.
- `GET /books/{id}` — fetch one book.
- `PUT /books/{id}` — update supplied fields, preserving omitted values.
- `DELETE /books/{id}` — delete a book.

Book objects contain `id`, `title`, `author`, `year`, and `isbn`. Missing optional values are returned as JSON `null`. Invalid input returns a JSON error object and an appropriate 4xx status.

## Tests

```sh
make test
```

The C unit tests cover JSON escaping, request-field parsing, and SQLite create/read/update/delete plus author filtering. They run without opening a network port.

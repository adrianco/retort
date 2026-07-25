# Book Collection REST API (Objective-C)

A dependency-free REST API for managing a book collection, written in
Objective-C with Foundation. It uses a small built-in HTTP/1.1 server (BSD
sockets + GCD) and stores data in SQLite via the system `libsqlite3`.

## Requirements

- macOS with the Xcode Command Line Tools (`clang`, `make`, and the macOS SDK,
  which provides Foundation and `libsqlite3`).

## Build

```sh
make            # builds ./bookserver (the API) and ./booktests (the tests)
```

## Run

```sh
make run        # or: ./bookserver
```

The server listens on `http://127.0.0.1:8080` by default and stores data in
`books.db` in the working directory. Both are configurable via environment
variables:

```sh
PORT=9090 BOOKS_DB=/tmp/mybooks.db ./bookserver
```

## Test

```sh
make test
```

This builds and runs `booktests`, which boots the real server on an ephemeral
port with a temporary database and exercises every endpoint over HTTP
(33 assertions covering create/read/update/delete, the author filter,
validation errors, 404s, and 405s). It exits non-zero on any failure.

## API

A book looks like:

```json
{"id": 1, "title": "Release It!", "author": "Michael Nygard", "year": 2018, "isbn": "978-1680502398"}
```

`title` and `author` are required non-empty strings; `year` (integer) and
`isbn` (string) are optional and returned as `null` when absent.

| Method | Path              | Description                            | Success | Errors |
|--------|-------------------|----------------------------------------|---------|--------|
| GET    | `/health`         | Health check: `{"status":"ok"}`        | 200     |        |
| POST   | `/books`          | Create a book (JSON body)              | 201     | 400    |
| GET    | `/books`          | List all books; `?author=` exact filter| 200     |        |
| GET    | `/books/{id}`     | Get one book                           | 200     | 404    |
| PUT    | `/books/{id}`     | Replace a book (JSON body)             | 200     | 400, 404 |
| DELETE | `/books/{id}`     | Delete a book                          | 204     | 404    |

Invalid JSON, missing/blank `title` or `author`, or wrongly-typed fields
return `400` with `{"error": "<message>"}`. Unknown paths return `404`, and
unsupported methods on known paths return `405`.

### Examples

```sh
curl -X POST localhost:8080/books \
     -d '{"title":"Release It!","author":"Michael Nygard","year":2018}'

curl 'localhost:8080/books?author=Michael%20Nygard'

curl -X PUT localhost:8080/books/1 \
     -d '{"title":"Release It! 2nd Ed.","author":"Michael Nygard","year":2018}'

curl -X DELETE localhost:8080/books/1
```

## Project layout

| File           | Purpose                                                    |
|----------------|------------------------------------------------------------|
| `HTTPServer.h/m` | Minimal blocking-socket HTTP/1.1 server (loopback only)  |
| `BookStore.h/m`  | SQLite-backed CRUD store (thread-safe via a serial queue)|
| `BookAPI.h/m`    | Routing and input validation                             |
| `main.m`         | Server entry point                                       |
| `tests.m`        | Integration test suite                                   |

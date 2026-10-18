# Book Collection API (Objective-C)

A REST service for managing a book collection. It is written in Objective-C on
Foundation, stores data in SQLite (the system `libsqlite3`), and serves HTTP
over a small BSD-socket server, so there are no third-party dependencies.

## Requirements

- macOS with Xcode command-line tools (`clang`, the macOS SDK). Run `xcode-select --install` if needed.
- Nothing else. SQLite ships with macOS.

## Build

```sh
make          # builds bin/bookservice
make test     # builds bin/tests and runs the test suite
make clean
```

## Run

```sh
make && ./bin/bookservice
```

Configuration is through environment variables:

| Variable        | Default          | Meaning                                  |
|-----------------|------------------|------------------------------------------|
| `PORT`          | `8080`           | TCP port, bound to `127.0.0.1` only      |
| `BOOKS_DB_PATH` | `./books.sqlite` | SQLite file (created on first run)       |

```sh
PORT=9000 BOOKS_DB_PATH=/tmp/books.sqlite ./bin/bookservice
```

## API

A book has `id`, `title`, `author`, `year` and `isbn`. `title` and `author` are
required and must be non-blank strings. `year` is an optional integer from 0 to
9999. `isbn` is an optional string. Responses are JSON.

| Method   | Path              | Success                          | Errors                                  |
|----------|-------------------|----------------------------------|-----------------------------------------|
| `POST`   | `/books`          | `201` with body and `Location`   | `400` validation or invalid JSON        |
| `GET`    | `/books`          | `200` array of books             |                                         |
| `GET`    | `/books?author=X` | `200` books whose author matches X (case-insensitive) | |
| `GET`    | `/books/{id}`     | `200`                            | `400` bad id, `404` not found           |
| `PUT`    | `/books/{id}`     | `200` updated book (full replacement; title and author still required) | `400`, `404` |
| `DELETE` | `/books/{id}`     | `204` no content                 | `400` bad id, `404` not found           |
| `GET`    | `/health`         | `200` `{"status":"ok"}`          | `503` if the database is unavailable    |

Errors have the form `{"error": "message"}`. Unknown paths return `404`, and a
known path with an unsupported method returns `405` with an `Allow` header.

### Examples

```sh
# Create
curl -i -X POST http://127.0.0.1:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Dispossessed","author":"Ursula K. Le Guin","year":1974,"isbn":"9780061054884"}'

# List, filtered by author
curl 'http://127.0.0.1:8080/books?author=Ursula%20K.%20Le%20Guin'

# Get, update, delete
curl http://127.0.0.1:8080/books/1
curl -X PUT http://127.0.0.1:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Dispossessed","author":"Ursula K. Le Guin","year":1974}'
curl -i -X DELETE http://127.0.0.1:8080/books/1

# Health
curl http://127.0.0.1:8080/health
```

## Project layout

```
src/
  Book.h/.m          model, input validation, JSON conversion
  BookStore.h/.m     SQLite persistence (prepared statements)
  BookAPI.h/.m       routing and handlers; no socket code, so it is testable directly
  HTTP.h/.m          HTTPRequest / HTTPResponse value types and serialization
  HTTPServer.h/.m    single-threaded HTTP/1.1 server over BSD sockets
  main.m             entry point and configuration
tests/
  BookServiceTests.m unit, persistence, routing and end-to-end socket tests
Makefile
```

## Design notes

- The server handles one request per connection (`Connection: close`) and
  processes requests serially. SQLite access is therefore single-threaded.
- It binds to loopback only. Chunked request bodies are rejected with `501`.
  Bodies are limited to 1 MB and header blocks to 16 KB.
- Tests use an in-memory SQLite database. The end-to-end test starts the real
  server on an OS-assigned port and talks to it over a socket.

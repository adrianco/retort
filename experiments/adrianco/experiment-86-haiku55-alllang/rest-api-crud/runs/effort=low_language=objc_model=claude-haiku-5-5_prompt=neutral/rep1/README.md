# Books API

A REST service for managing a book collection, written in Objective-C. It uses Foundation for JSON,
SQLite (`libsqlite3`) for storage, and a small POSIX-socket HTTP server, so it has no third-party dependencies.

## Requirements

- macOS with the Xcode command-line tools (`clang`, the macOS SDK with `sqlite3.h`)

## Build, test, run

```sh
make          # builds build/books-api
make test     # builds and runs build/tests
make run      # starts the server
```

The server reads two environment variables:

| Variable        | Default     | Purpose                              |
|-----------------|-------------|--------------------------------------|
| `PORT`          | `8080`      | TCP port to listen on (all interfaces) |
| `BOOKS_DB_PATH` | `books.db`  | SQLite database file, created if missing |

```sh
PORT=8080 BOOKS_DB_PATH=./books.db ./build/books-api
```

## Data model

| Field    | Type    | Rules                                   |
|----------|---------|-----------------------------------------|
| `id`     | integer | Assigned by the server, read-only       |
| `title`  | string  | Required, non-blank                     |
| `author` | string  | Required, non-blank                     |
| `year`   | integer | Optional, 0–9999                        |
| `isbn`   | string  | Optional                                |

Strings are trimmed of surrounding whitespace before they are stored.

## Endpoints

| Method   | Path           | Success          | Description |
|----------|----------------|------------------|-------------|
| `POST`   | `/books`       | `201` + book     | Create a book |
| `GET`    | `/books`       | `200` + array    | List all books, ordered by id. `?author=<name>` returns exact matches. |
| `GET`    | `/books/{id}`  | `200` + book     | Get one book |
| `PUT`    | `/books/{id}`  | `200` + book     | Replace a book. The same fields are required as for `POST`; omitted optional fields are cleared. |
| `DELETE` | `/books/{id}`  | `204`            | Delete a book (no body) |
| `GET`    | `/health`      | `200` `{"status":"ok"}` | Health check |

Error responses are JSON, shaped as `{"error": "..."}`. Validation failures add a `details` array:

| Status | When |
|--------|------|
| `400`  | Body is not a JSON object |
| `404`  | Unknown route, non-numeric id, or no book with that id |
| `405`  | Method not supported for the route |
| `413`  | Headers or body too large (headers > 16 KB, body > 1 MB) |
| `422`  | Validation failed, e.g. missing `title` or `author` |
| `500`  | Database error |

### Examples

```sh
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl "localhost:8080/books?author=Frank%20Herbert"

curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

## Layout

```
src/
  BookStore.{h,m}   SQLite persistence (prepared statements, parameter binding)
  BookAPI.{h,m}     Routing, validation, and status codes; no socket code
  HTTPServer.{h,m}  HTTP/1.1 parsing and response writing over POSIX sockets
  main.m            Reads configuration and starts the server
tests/
  test_main.m       Unit tests for the store and router, plus end-to-end socket tests
Makefile
```

## Design notes

- The server handles one connection at a time and closes each connection after responding. This keeps the
  HTTP layer small. It is fine for a local or single-user service, but not for high concurrent load.
- Each request runs its own SQL statements. The database is opened with `SQLITE_OPEN_FULLMUTEX`, so
  the store is safe to use from more than one thread.
- The tests are a small self-contained harness, so they run with `make test` and do not need Xcode's
  XCTest. They cover create, read, list with the author filter, update, delete, validation, routing, and one
  end-to-end run over a real loopback socket.

# Book Collection API (Objective-C)

A REST service for managing a book collection. It uses Foundation, a small BSD-socket HTTP/1.1 server, and SQLite (`libsqlite3`, which ships with macOS).

## Requirements

- macOS with Xcode or the Command Line Tools (provides `clang`, the Foundation framework, and the SQLite SDK headers)

## Build, test, and run

```sh
make test   # build and run the test suite
make        # build build/bookapi
make run    # build and start the server
```

The server listens on `127.0.0.1:8080` by default. Configure it with environment variables:

| Variable   | Default    | Meaning                                  |
|------------|------------|------------------------------------------|
| `PORT`     | `8080`     | Port to listen on                        |
| `BOOKS_DB` | `books.db` | SQLite database file (created if absent) |

```sh
PORT=3000 BOOKS_DB=/tmp/books.db ./build/bookapi
```

## Data model

| Field    | Type    | Required | Notes                                |
|----------|---------|----------|--------------------------------------|
| `id`     | integer | —        | Assigned by the server               |
| `title`  | string  | yes      | Non-empty after trimming whitespace  |
| `author` | string  | yes      | Non-empty after trimming whitespace  |
| `year`   | integer | no       | Must be a JSON integer, not a string |
| `isbn`   | string  | no       | Empty string is treated as absent    |

## Endpoints

| Method   | Path           | Description                                              | Success   |
|----------|----------------|----------------------------------------------------------|-----------|
| `POST`   | `/books`       | Create a book                                            | `201` + book, `Location` header |
| `GET`    | `/books`       | List books; `?author=` filters by case-insensitive exact author match | `200` + array |
| `GET`    | `/books/{id}`  | Get one book                                             | `200` + book |
| `PUT`    | `/books/{id}`  | Update a book. Fields omitted from the body keep their values; `null` clears `year` or `isbn` | `200` + book |
| `DELETE` | `/books/{id}`  | Delete a book                                            | `204`     |
| `GET`    | `/health`      | Health check                                             | `200` `{"status":"ok"}` |

Errors return a JSON body of the form `{"error": "..."}`:

- `400` — invalid JSON, missing or invalid fields, or a non-positive-integer id
- `404` — unknown book or unknown route
- `405` — method not supported on that route (includes an `Allow` header)
- `413` — headers over 64 KB or body over 1 MB
- `500` — database failure

## Examples

```sh
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -H 'Content-Type: application/json' -d '{"year":1966}'
curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

## Layout

```
src/
  Book.{h,m}          Model, validation, JSON representation
  BookStore.{h,m}     SQLite persistence
  BookAPI.{h,m}       Request routing and handlers (no socket code)
  HTTPMessage.{h,m}   Request and response value types
  HTTPServer.{h,m}    Minimal blocking HTTP/1.1 server (loopback only)
  main.m              Entry point
tests/main.m          Unit and integration tests
```

## Notes and limitations

- The server binds to the loopback interface only and handles one connection at a time. It is intended for local use, not as a production deployment.
- Each connection is closed after one response (`Connection: close`); keep-alive and chunked request bodies are not supported.

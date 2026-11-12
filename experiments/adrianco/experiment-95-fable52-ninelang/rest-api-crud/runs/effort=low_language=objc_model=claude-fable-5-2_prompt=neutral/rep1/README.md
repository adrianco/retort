# Book Collection REST API (Objective-C)

A small REST service for managing books, written in Objective-C with only
system libraries: Foundation, BSD sockets for HTTP, and SQLite (`libsqlite3`)
for storage. No third-party dependencies.

## Requirements

- macOS with the Xcode Command Line Tools (`clang`, `make`)

## Build, run, test

```sh
make            # builds build/bookapi
make run        # builds and starts the server
make test       # builds and runs the test suite
make clean
```

Configuration is through environment variables:

| Variable  | Default    | Meaning                                  |
|-----------|------------|------------------------------------------|
| `PORT`    | `8080`     | TCP port to listen on                    |
| `DB_PATH` | `books.db` | SQLite database file (created if absent) |

```sh
PORT=9000 DB_PATH=/tmp/books.db ./build/bookapi
```

## API

All request and response bodies are JSON.

| Method | Path          | Success       | Errors        |
|--------|---------------|---------------|---------------|
| GET    | `/health`     | 200           | 503           |
| POST   | `/books`      | 201 + book    | 400, 422      |
| GET    | `/books`      | 200 + array   |               |
| GET    | `/books/{id}` | 200 + book    | 404           |
| PUT    | `/books/{id}` | 200 + book    | 400, 404, 422 |
| DELETE | `/books/{id}` | 204 (no body) | 404           |

`GET /books?author=Name` returns only books by that author (exact match,
case-insensitive).

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

Validation rules for `POST` and `PUT`:

- `title` and `author` are required, non-empty strings
- `year` is optional and must be an integer
- `isbn` is optional and must be a string
- `PUT` replaces the whole book, so omitted optional fields become `null`

Error responses have the form `{"error": "..."}`; validation failures (422)
also include a `details` array listing each problem. Malformed JSON gives 400,
unsupported methods 405, and bodies over 1 MB 413.

### Examples

```sh
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl localhost:8080/books
curl 'localhost:8080/books?author=Frank%20Herbert'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune Messiah","author":"Frank Herbert"}'
curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

## Layout

```
src/BookStore.{h,m}   SQLite persistence (prepared statements, thread-safe)
src/BooksAPI.{h,m}    Routing, validation, JSON responses (no networking)
src/HTTPServer.{h,m}  Minimal HTTP/1.1 server on BSD sockets + GCD
src/main.m            Entry point
tests/test_main.m     Test runner: API-level tests plus an end-to-end HTTP test
```

The tests use a small self-contained runner rather than XCTest so they build
with plain `clang`. They cover each endpoint, validation, the author filter,
on-disk persistence, and a full CRUD cycle over a real socket.

## Limitations

- One request per connection (`Connection: close`); no keep-alive, TLS or
  chunked request bodies.
- No authentication, and the server listens on all interfaces.

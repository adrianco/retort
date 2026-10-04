# Books API (Objective-C)

A REST service for managing a book collection, written in Objective-C using only
Foundation, BSD sockets and the system SQLite library — no third-party dependencies.

## Requirements

- macOS with the Xcode Command Line Tools (`clang`, `make`); `xcode-select --install`

## Build, run, test

```sh
make          # builds build/books-api
make run      # builds and starts the server
make test     # builds and runs the test suite
make clean
```

Configuration is via environment variables:

| Variable  | Default    | Meaning                   |
|-----------|------------|---------------------------|
| `PORT`    | `8080`     | TCP port to listen on     |
| `DB_PATH` | `books.db` | SQLite database file path |

```sh
PORT=9000 DB_PATH=/tmp/books.db ./build/books-api
```

## API

All request and response bodies are JSON. Errors look like `{"error": "..."}`;
validation errors also carry a `details` array.

| Method | Path          | Success | Errors   | Notes                                         |
|--------|---------------|---------|----------|-----------------------------------------------|
| GET    | `/health`     | 200     |          | `{"status":"ok"}`                             |
| POST   | `/books`      | 201     | 400      | Creates a book, returns it with its `id`      |
| GET    | `/books`      | 200     |          | `?author=` filters (exact, case-insensitive)  |
| GET    | `/books/{id}` | 200     | 404      |                                               |
| PUT    | `/books/{id}` | 200     | 400, 404 | Full replacement; omitted optional fields become `null` |
| DELETE | `/books/{id}` | 204     | 404      | Empty body                                    |

Unsupported methods on a known path return 405; bodies over 1 MB return 413.

Book fields:

- `title` — string, required, non-empty
- `author` — string, required, non-empty
- `year` — integer, optional
- `isbn` — string, optional

### Example

```sh
curl -i -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune Messiah","author":"Frank Herbert"}'
curl -i -X DELETE localhost:8080/books/1
```

## Layout

- `src/BookStore.{h,m}` — SQLite persistence
- `src/BookAPI.{h,m}` — routing, validation, status codes (transport-independent)
- `src/HTTPServer.{h,m}` — minimal HTTP/1.1 server (one request per connection)
- `src/main.m` — entry point
- `tests/test_main.m` — API tests on an in-memory database plus end-to-end tests
  over real HTTP against a server on an ephemeral port

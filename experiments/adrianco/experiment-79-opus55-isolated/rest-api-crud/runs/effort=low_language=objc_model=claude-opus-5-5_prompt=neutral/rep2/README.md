# Books API (Objective-C)

A small REST service for managing a book collection, written in Objective-C
with Foundation, BSD sockets, and SQLite. No third-party dependencies.

## Requirements

- macOS with the Xcode Command Line Tools (`clang`, `make`, the system `libsqlite3`)

## Build, run, test

```sh
make            # builds build/books-api
make run        # builds and starts the server
make test       # builds and runs the test suite
make clean
```

Configuration is via environment variables:

| Variable  | Default     | Meaning                                   |
|-----------|-------------|-------------------------------------------|
| `PORT`    | `8080`      | TCP port to listen on                     |
| `HOST`    | `127.0.0.1` | IPv4 address to bind (`0.0.0.0` for all)  |
| `DB_PATH` | `books.db`  | SQLite database file (created if missing) |

```sh
PORT=9000 DB_PATH=/tmp/books.db ./build/books-api
```

## API

All request and response bodies are JSON. A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

| Method | Path          | Success          | Errors     |
|--------|---------------|------------------|------------|
| GET    | `/health`     | 200 `{"status":"ok"}` |       |
| POST   | `/books`      | 201, created book | 400       |
| GET    | `/books`      | 200, array of books (optional `?author=` filter) | |
| GET    | `/books/{id}` | 200, book        | 404        |
| PUT    | `/books/{id}` | 200, updated book | 400, 404  |
| DELETE | `/books/{id}` | 204, empty body  | 404        |

Other statuses: 404 for unknown paths, 405 (with an `Allow` header) for
unsupported methods, 413 for bodies over 1 MB.

Behaviour worth knowing:

- `title` and `author` are required, non-blank strings (surrounding whitespace is trimmed).
- `year` (integer) and `isbn` (string) are optional and are returned as `null` when absent.
- `PUT` is a full replacement: it is validated like `POST`, and omitted optional fields become `null`.
- The `?author=` filter is an exact, case-insensitive match.
- Errors look like `{"error": "..."}`; validation errors add a `details` array:
  `{"error":"validation failed","details":["title is required"]}`.

### Example

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:8080/books/1
```

## Layout

- `src/BookStore.{h,m}` — SQLite persistence (prepared statements throughout)
- `src/BooksAPI.{h,m}` — routing, validation, JSON responses; independent of the transport
- `src/HTTPServer.{h,m}` — minimal HTTP/1.1 server (one request per connection)
- `src/main.m` — entry point
- `tests/test_main.m` — self-contained test runner: unit tests against `BooksAPI`
  with an in-memory database, plus integration tests over real HTTP on an ephemeral port

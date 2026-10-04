# Book API

A REST service for managing a book collection, written in Swift with no
third-party dependencies: the HTTP server is built on Apple's Network.framework
and data is stored in SQLite via the system `sqlite3` library.

## Requirements

- macOS 12 or later
- Swift 5.9+ toolchain (Xcode or the Xcode command line tools)

## Run

```bash
swift run bookapi-server
```

The server listens on port 8080 and stores data in `books.db` in the current
directory. Both are configurable through environment variables:

| Variable  | Default    | Meaning                                         |
|-----------|------------|-------------------------------------------------|
| `PORT`    | `8080`     | TCP port to listen on                           |
| `DB_PATH` | `books.db` | SQLite database file (`:memory:` for transient) |

```bash
PORT=9000 DB_PATH=/tmp/books.db swift run bookapi-server
```

## Test

```bash
swift test
```

The tests cover the router against an in-memory database, the HTTP parser,
persistence across reopening the database file, and a full lifecycle over a
real socket.

## API

A book looks like this; `year` and `isbn` are optional and returned as `null`
when absent:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

| Method | Path          | Success          | Errors                               |
|--------|---------------|------------------|--------------------------------------|
| GET    | `/health`     | 200 `{"status":"ok"}` |                                 |
| POST   | `/books`      | 201 book, `Location` header | 400 validation failed     |
| GET    | `/books`      | 200 array of books |                                    |
| GET    | `/books/{id}` | 200 book         | 400 bad id, 404 not found            |
| PUT    | `/books/{id}` | 200 book         | 400 bad id / validation, 404 not found |
| DELETE | `/books/{id}` | 204 no body      | 400 bad id, 404 not found            |

- `GET /books?author=Name` returns only books by that author (exact match,
  case-insensitive).
- `PUT` replaces the whole book: omitted optional fields are cleared.
- Validation: `title` and `author` are required non-empty strings, `year` must
  be an integer, `isbn` must be a string.
- Unsupported methods return 405 with an `Allow` header; unknown paths return 404.

Errors are JSON:

```json
{"error": "validation failed", "details": ["title is required"]}
```

### Examples

```bash
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl localhost:8080/books
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -i -X DELETE localhost:8080/books/1
```

## Layout

- `Sources/BookAPI/` — library: model and validation (`Book.swift`), SQLite
  storage (`BookStore.swift`), routing (`Router.swift`), HTTP parsing and
  serialization (`HTTP.swift`), socket server (`Server.swift`)
- `Sources/bookapi-server/` — executable entry point
- `Tests/BookAPITests/` — tests

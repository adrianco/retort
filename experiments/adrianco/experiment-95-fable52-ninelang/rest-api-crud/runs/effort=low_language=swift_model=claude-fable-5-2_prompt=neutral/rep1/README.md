# Book API

A REST service for managing a book collection, written in Swift with **no
third-party dependencies**: HTTP is served with Apple's `Network` framework and
data is stored in SQLite via the system `sqlite3` library.

## Requirements

- macOS 12+
- Swift 5.9+ toolchain (Xcode or swift.org)

## Run

```bash
swift run bookapi-server
```

Configuration is via environment variables:

| Variable  | Default    | Description                                   |
|-----------|------------|-----------------------------------------------|
| `PORT`    | `8080`     | TCP port to listen on                         |
| `DB_PATH` | `books.db` | SQLite file (`:memory:` for a non-persistent DB) |

```bash
PORT=9000 DB_PATH=/tmp/books.db swift run bookapi-server
```

## Test

```bash
swift test
```

The suite covers the router against an in-memory database, the HTTP parser,
on-disk persistence, and a full CRUD lifecycle over a real TCP socket.

## API

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

`title` and `author` are required, non-blank strings. `year` (integer) and
`isbn` (string) are optional and returned as `null` when absent.

| Method | Path          | Description                                  | Success | Errors        |
|--------|---------------|----------------------------------------------|---------|---------------|
| GET    | `/health`     | Health check: `{"status":"ok"}`              | 200     |               |
| POST   | `/books`      | Create a book                                | 201     | 400           |
| GET    | `/books`      | List books; `?author=` filters by author     | 200     |               |
| GET    | `/books/{id}` | Fetch one book                               | 200     | 400, 404      |
| PUT    | `/books/{id}` | Replace a book (full update, same rules as POST) | 200 | 400, 404      |
| DELETE | `/books/{id}` | Delete a book                                | 204     | 400, 404      |

Notes:

- The `author` filter is an exact, case-insensitive match.
- `PUT` replaces the whole record; optional fields omitted from the body are cleared.
- Errors are JSON: `{"error": "validation failed", "details": ["title is required"]}`.
  Invalid JSON, failed validation and non-numeric ids return 400; unknown
  paths/ids return 404; unsupported methods return 405 with an `Allow` header.
- Request bodies are limited to 1 MB; chunked request bodies are not supported.

### Examples

```bash
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune Messiah","author":"Frank Herbert"}'
curl -X DELETE localhost:8080/books/1
```

## Layout

- `Sources/BookAPI/Book.swift` — model and input validation
- `Sources/BookAPI/BookStore.swift` — SQLite repository
- `Sources/BookAPI/Router.swift` — request → response routing
- `Sources/BookAPI/HTTP.swift` — request/response types and HTTP/1.1 parser
- `Sources/BookAPI/HTTPServer.swift` — `Network.framework` listener
- `Sources/bookapi-server/main.swift` — executable entry point
- `Tests/BookAPITests/` — tests

# Book API

A REST service for managing a book collection, written in Swift with no third-party
dependencies: a small HTTP/1.1 server on POSIX sockets and the system SQLite library.

## Requirements

- macOS 13+ with Swift 5.9 or later (Xcode or the Swift toolchain)

## Run

```bash
swift run bookapi-server
```

Configuration is via environment variables:

| Variable  | Default        | Description                                  |
|-----------|----------------|----------------------------------------------|
| `PORT`    | `8080`         | Port to listen on                            |
| `HOST`    | `127.0.0.1`    | IPv4 address to bind (`0.0.0.0` for all)     |
| `DB_PATH` | `books.sqlite` | SQLite database file (`:memory:` for no file) |

## Test

```bash
swift test
```

The tests cover the routing/validation layer directly against an in-memory database,
and the full stack end to end over a real socket.

## API

A book has `id` (assigned by the server), `title` and `author` (required, non-empty
strings), and optional `year` (integer) and `isbn` (string). Omitted optional fields
are returned as `null`.

| Method | Path          | Description                          | Success | Errors   |
|--------|---------------|--------------------------------------|---------|----------|
| GET    | `/health`     | Health check                         | 200     | 503      |
| POST   | `/books`      | Create a book                        | 201     | 400      |
| GET    | `/books`      | List books; `?author=` filters       | 200     |          |
| GET    | `/books/{id}` | Get one book                         | 200     | 400, 404 |
| PUT    | `/books/{id}` | Replace a book (all fields, as POST) | 200     | 400, 404 |
| DELETE | `/books/{id}` | Delete a book                        | 204     | 400, 404 |

The `author` filter matches the whole author name, ignoring ASCII case. Unknown paths
return 404 and unsupported methods 405. Errors are JSON:

```json
{"error": "validation failed", "details": ["title is required"]}
```

## Examples

```bash
curl -i -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl localhost:8080/books
curl 'localhost:8080/books?author=Frank%20Herbert'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -i -X DELETE localhost:8080/books/1
```

## Layout

- `Sources/BookAPI/BookStore.swift` — SQLite persistence
- `Sources/BookAPI/App.swift` — routing, validation, JSON responses
- `Sources/BookAPI/Server.swift` — HTTP server
- `Sources/bookapi-server/main.swift` — executable entry point
- `Tests/BookAPITests` — tests

# Book API

A REST API for managing a book collection, written in Swift with no third-party
dependencies: the HTTP server is built on Network.framework and data is stored in
SQLite through the system `sqlite3` library.

## Requirements

- macOS 13 or later
- Swift 5.9 or later (Xcode or the Swift toolchain)

## Run

```bash
swift run BookServer
```

The server listens on `http://localhost:8080` and stores data in `books.db` in the
current directory. Both can be changed with environment variables:

| Variable  | Default    | Meaning                                         |
|-----------|------------|-------------------------------------------------|
| `PORT`    | `8080`     | TCP port to listen on                           |
| `DB_PATH` | `books.db` | SQLite file path (`:memory:` for non-persistent) |

```bash
PORT=9000 DB_PATH=/tmp/books.db swift run BookServer
```

## Test

```bash
swift test
```

The tests cover the routes and validation against an in-memory database, SQLite
persistence, HTTP request parsing, and one end-to-end run over a real socket.

## API

A book looks like this; `year` and `isbn` are optional and returned as `null` when unset.

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

| Method | Path          | Description                          | Success | Errors        |
|--------|---------------|--------------------------------------|---------|---------------|
| GET    | `/health`     | Health check, returns `{"status":"ok"}` | 200  |               |
| POST   | `/books`      | Create a book                        | 201     | 400, 422      |
| GET    | `/books`      | List books, optional `?author=` filter | 200   |               |
| GET    | `/books/{id}` | Get one book                         | 200     | 404           |
| PUT    | `/books/{id}` | Replace a book                       | 200     | 400, 404, 422 |
| DELETE | `/books/{id}` | Delete a book                        | 204     | 404           |

Behaviour worth knowing:

- `title` and `author` are required non-blank strings; `year` must be an integer and
  `isbn` a string when present. Validation failures return 422 with a `details` list;
  a body that is not a JSON object returns 400.
- `PUT` is a full replacement: omitted optional fields are cleared.
- The `author` filter is a case-insensitive exact match.
- Unsupported methods on a known path return 405 with an `Allow` header.
- Errors are JSON: `{"error": "book not found"}`.

### Examples

```bash
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl localhost:8080/books
curl 'localhost:8080/books?author=Frank%20Herbert'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

## Layout

- `Sources/BookAPI` — library: model and validation (`Book.swift`), SQLite storage
  (`BookStore.swift`), HTTP parsing/serialisation (`HTTP.swift`), routing
  (`Router.swift`), socket server (`Server.swift`)
- `Sources/BookServer` — executable entry point
- `Tests/BookAPITests` — tests

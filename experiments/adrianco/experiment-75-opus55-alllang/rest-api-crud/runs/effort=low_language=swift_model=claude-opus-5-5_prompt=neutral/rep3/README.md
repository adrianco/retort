# Book Collection REST API (Swift)

A dependency-free Swift REST service for managing books. It uses the system SQLite3 library for storage and Network.framework for HTTP.

## Requirements
- macOS 13+ with Swift 5.9+ (Xcode or the command-line tools)

## Run
```sh
swift run BookServer              # listens on :8080, stores data in ./books.db
PORT=3000 DB_PATH=/tmp/b.db swift run BookServer
```

## Test
```sh
swift test
```

## Endpoints
| Method | Path | Success | Errors |
|---|---|---|---|
| GET | /health | 200 `{"status":"ok"}` | |
| POST | /books | 201 created book | 400 bad JSON, 422 validation |
| GET | /books[?author=Name] | 200 array (author match ignores case) | |
| GET | /books/{id} | 200 book | 400 bad id, 404 |
| PUT | /books/{id} | 200 updated book (full replace) | 400, 404, 422 |
| DELETE | /books/{id} | 204 | 404 |

Book body: `{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}`.
`title` and `author` are required and can't be blank. `year` (0–9999) and `isbn` are optional.

```sh
curl -XPOST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank%20Herbert'
```

## Layout
- `Sources/BookAPI/BookStore.swift`: SQLite repository
- `Sources/BookAPI/Router.swift`: routing, validation and JSON (doesn't depend on the transport)
- `Sources/BookAPI/HTTPServer.swift`: minimal HTTP/1.1 server
- `Sources/BookServer/main.swift`: entry point
- `Tests/BookAPITests`: XCTest suite

# Book Collection API (Swift)

A dependency-free REST service in Swift using Network.framework for HTTP and the system SQLite library for storage (macOS 13+).

## Build & run

```sh
swift build
swift run BookServer            # listens on :8080, stores data in ./books.db
PORT=9000 DB_PATH=/tmp/b.db swift run BookServer
```

## Endpoints

| Method | Path | Result |
|---|---|---|
| GET | /health | 200 `{"status":"ok"}` |
| POST | /books | 201 created book; 400 if title/author missing or JSON is invalid |
| GET | /books[?author=Name] | 200 list, optionally filtered by author |
| GET | /books/{id} | 200 book or 404 |
| PUT | /books/{id} | 200 updated book, 400 validation error, or 404 |
| DELETE | /books/{id} | 204 or 404 |

Book body: `{"title": "...", "author": "...", "year": 1965, "isbn": "..."}` (`year` and `isbn` are optional).

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank%20Herbert'
```

## Tests

```sh
swift test
```

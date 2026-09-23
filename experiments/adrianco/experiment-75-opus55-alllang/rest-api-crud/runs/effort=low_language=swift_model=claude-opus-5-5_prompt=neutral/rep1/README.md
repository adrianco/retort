# Book API (Swift)

A REST service for managing a book collection. Written in Swift with no third-party
dependencies: HTTP via Apple's Network.framework, storage in SQLite (system `libsqlite3`).

## Requirements
- macOS 13+ with Swift 5.9+ (tested with Swift 6.3)

## Run
```sh
swift run BookServer            # listens on :8080, stores data in ./books.db
PORT=9000 DB_PATH=/tmp/b.db swift run BookServer
```

## Endpoints
| Method | Path | Result |
|---|---|---|
| GET | /health | 200 `{"status":"ok"}` |
| POST | /books | 201 created book; 400 on validation error |
| GET | /books[?author=Name] | 200 list (author filter is case-insensitive exact match) |
| GET | /books/{id} | 200 book, 404 if missing |
| PUT | /books/{id} | 200 updated book, 400 invalid, 404 missing |
| DELETE | /books/{id} | 204, 404 if missing |

Body: `{"title": "...", "author": "...", "year": 1965, "isbn": "..."}` — `title` and `author` are required.

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank%20Herbert'
```

## Test
```sh
swift test
```
Tests cover CRUD, validation, filtering, error routes, and HTTP request parsing.

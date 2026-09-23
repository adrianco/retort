# Books REST API (C++17 + SQLite)

A small REST service for managing a book collection. It has no third-party
dependencies: it uses POSIX sockets for HTTP, the system `libsqlite3` for storage,
and a small built-in JSON parser.

## Requirements
- A C++17 compiler (clang or g++)
- SQLite3 development headers/library (built into macOS; `apt install libsqlite3-dev` on Debian/Ubuntu)
- make

## Build & test
```sh
make          # builds ./books_server and ./test_api
make test     # runs the test suite (in-memory SQLite)
```

## Run
```sh
./books_server [port] [db_path]    # defaults: 8080, books.db (or env PORT / DB_PATH)
```

## Endpoints
| Method | Path | Description | Success |
|---|---|---|---|
| GET | `/health` | Health check | 200 `{"status":"ok"}` |
| POST | `/books` | Create a book | 201 + book |
| GET | `/books[?author=Name]` | List books, optionally filtered by exact author | 200 + array |
| GET | `/books/{id}` | Get a book | 200 / 404 |
| PUT | `/books/{id}` | Replace a book | 200 / 400 / 404 |
| DELETE | `/books/{id}` | Delete a book | 204 / 404 |

Book JSON: `{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}`.
`title` and `author` are required non-empty strings; `year` is an optional integer; `isbn` an optional string.
Validation errors return `400 {"error":"..."}`.

## Example
```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:8080/books/1
```

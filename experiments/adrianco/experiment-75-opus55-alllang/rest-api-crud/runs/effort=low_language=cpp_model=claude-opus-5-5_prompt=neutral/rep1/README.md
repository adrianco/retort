# Book Collection REST API (C++17 + SQLite)

A dependency-light REST service: a small built-in HTTP/1.1 server (POSIX sockets) plus SQLite storage.

## Requirements
- C++17 compiler (clang or gcc), `make`
- SQLite3 dev library (preinstalled on macOS; `apt install libsqlite3-dev` on Debian/Ubuntu)

## Build & run
```sh
make                       # builds ./book_server and ./test_api
./book_server [port] [db]  # defaults: 8080 books.db
```

## Test
```sh
make test
```
Tests exercise the request handler against an in-memory SQLite DB (CRUD, filtering, validation, status codes).

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | body `{title, author, year?, isbn?}` → 201 |
| GET | /books | optional `?author=` exact-match filter |
| GET | /books/{id} | 200 or 404 |
| PUT | /books/{id} | full replace; same validation as POST → 200/400/404 |
| DELETE | /books/{id} | 204 or 404 |

`title` and `author` are required non-empty strings; `year` must be an integer; `isbn` a string. Errors return `{"error": "..."}` with 400/404/405.

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank%20Herbert'
```

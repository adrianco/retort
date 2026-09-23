# Book Collection REST API (C + SQLite)

A small HTTP/1.1 JSON API in plain C (POSIX sockets, no framework) backed by SQLite.

## Requirements
- C compiler (clang/gcc), `make`
- SQLite3 development library (`libsqlite3`; bundled with macOS SDK, `apt install libsqlite3-dev` on Debian/Ubuntu)
- `curl` (for the HTTP end-to-end test)

## Build & run
```sh
make                      # builds ./books_server
./books_server 8080       # or PORT=8080 ./books_server; DB file via BOOKS_DB (default books.db)
```

## Test
```sh
make test   # C unit/integration tests (in-memory DB) + curl end-to-end test
```

## Endpoints
| Method | Path | Success | Errors |
|---|---|---|---|
| GET | /health | 200 `{"status":"ok"}` | |
| POST | /books | 201 book | 400 invalid |
| GET | /books[?author=Name] | 200 array | |
| GET | /books/{id} | 200 book | 404 |
| PUT | /books/{id} | 200 book | 400, 404 |
| DELETE | /books/{id} | 204 | 404 |

Book body: `{"title": "...", "author": "...", "year": 1965, "isbn": "..."}` — `title` and `author`
are required non-empty strings; `year` (integer) and `isbn` (string) are optional. PUT replaces the
whole record with the same validation. Errors are `{"error": "message"}`.

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank%20Herbert'
```

Note: the server handles one connection at a time (simple, sequential accept loop).

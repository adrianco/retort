# Books REST API (C + SQLite)

A small REST service for managing a book collection, written in C11 using only
the system SQLite library and a minimal built-in HTTP/1.1 server.

## Requirements
- A C compiler (clang or gcc) and `make`
- SQLite 3 dev library (macOS: included in the SDK; Debian/Ubuntu: `apt install libsqlite3-dev`)

## Build & run
```sh
make                 # builds ./books_server
./books_server       # listens on port 8080, database file books.db
PORT=9000 DB_PATH=/tmp/books.db ./books_server
```

## Test
```sh
make test            # builds tests with ASan/UBSan and runs them against an in-memory DB
```

## Endpoints
| Method | Path | Description | Success |
|---|---|---|---|
| GET | /health | Health check | 200 `{"status":"ok"}` |
| POST | /books | Create book (`title`, `author` required; `year` int, `isbn` string optional) | 201 |
| GET | /books[?author=Name] | List books, optionally filtered by exact author | 200 |
| GET | /books/{id} | Get one book | 200 / 404 |
| PUT | /books/{id} | Replace book (same validation as POST) | 200 / 404 |
| DELETE | /books/{id} | Delete book | 204 / 404 |

Errors are JSON: `{"error":"..."}` with 400 (validation / bad JSON), 404, 405 or 500.

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'
curl 'localhost:8080/books?author=Frank%20Herbert'
```

## Layout
- `src/books.c` – routing, validation, JSON, SQLite access (transport-independent)
- `src/main.c` – socket HTTP server
- `tests/test_books.c` – tests

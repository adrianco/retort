# Book Collection REST API (C + SQLite)

A small REST service in plain C (POSIX sockets) with data stored in SQLite.

## Requirements
- A C compiler (`cc`/`gcc`/`clang`) and `make`
- SQLite3 development headers and library (macOS ships them; on Debian/Ubuntu: `apt install libsqlite3-dev`)

## Build, test, run
```sh
make            # builds ./books_server
make test       # builds and runs the unit/integration tests
./books_server  # listens on :8080, stores data in ./books.db
PORT=9000 BOOKS_DB=/tmp/books.db ./books_server   # override port and database file
```

## Endpoints
| Method | Path | Description | Success |
|---|---|---|---|
| GET | `/health` | Health check | 200 `{"status":"ok"}` |
| POST | `/books` | Create a book | 201 + book |
| GET | `/books[?author=Name]` | List books, optionally filtered by exact author | 200 + array |
| GET | `/books/{id}` | Get one book | 200 + book |
| PUT | `/books/{id}` | Replace a book | 200 + book |
| DELETE | `/books/{id}` | Delete a book | 204 |

Book JSON: `{"title": string, "author": string, "year": integer|null, "isbn": string|null}`.
`title` and `author` are required and must not be blank. Errors return `{"error": "..."}`
with 400 (validation/bad JSON), 404 (not found), or 405 (bad method).

## Example
```sh
curl -XPOST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'
curl 'localhost:8080/books?author=Frank%20Herbert'
```

## Layout
- `src/books.c` — routing, validation, JSON handling, SQLite access (transport-independent)
- `src/server.c` — HTTP/1.1 socket server (one request per connection, sequential)
- `tests/test_books.c` — tests exercising every endpoint against an in-memory database

# Book Collection REST API (Objective-C)

A small REST service in Objective-C (Foundation + BSD sockets) that stores books in SQLite.

## Requirements
macOS with Xcode command-line tools (`clang`, Foundation, libsqlite3).

## Build & run
```sh
make                 # builds ./bookserver
./bookserver         # listens on :8080, uses ./books.db
PORT=9000 DB_PATH=/tmp/books.db ./bookserver
```

## Test
```sh
make test
```
Tests use an in-memory SQLite DB and exercise the router directly.

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | body `{title, author, year?, isbn?}` → 201 |
| GET | /books | optional `?author=` exact-match filter |
| GET | /books/{id} | 404 if missing |
| PUT | /books/{id} | full replace, same validation as POST |
| DELETE | /books/{id} | 204 on success |

`title` and `author` are required non-blank strings; `year` must be an integer; `isbn` a string.
Errors return `{"error": "..."}` with 400/404/405.

Example:
```sh
curl -XPOST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
```

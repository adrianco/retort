# Book Collection REST API (Objective-C)

A small REST service written in Objective-C using Foundation, the system SQLite (`libsqlite3`) and a minimal built-in HTTP/1.1 server. It has no third-party dependencies.

## Requirements
macOS with the Xcode Command Line Tools (`clang`, Foundation and libsqlite3).

## Build & run
```sh
make                 # builds ./bookapi
./bookapi            # listens on :8080 and uses ./books.db
PORT=9000 DB_PATH=/tmp/books.db ./bookapi
```

## Test
```sh
make test
```
The tests run every endpoint against an in-memory SQLite database. They cover CRUD, the author filter, validation and 404/405 handling.

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | JSON body `{title, author, year?, isbn?}` → 201 |
| GET | /books | optional `?author=` exact-match filter |
| GET | /books/{id} | 200 or 404 |
| PUT | /books/{id} | full replacement, same validation as POST |
| DELETE | /books/{id} | 204 or 404 |

`title` and `author` are required non-blank strings, `year` must be an integer and `isbn` must be a string. If validation fails, the response is `400 {"error": "..."}`.

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank%20Herbert'
```

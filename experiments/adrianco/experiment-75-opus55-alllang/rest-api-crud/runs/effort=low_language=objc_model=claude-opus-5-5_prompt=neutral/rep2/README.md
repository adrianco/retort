# Book Collection REST API (Objective-C)

A small REST service in Objective-C that uses only Foundation, a built-in BSD-socket HTTP/1.1 server and SQLite (`libsqlite3`, which ships with macOS).

## Build & run
Requires macOS with the Xcode command-line tools.
```sh
make                       # builds ./bookserver
PORT=8080 DB_PATH=books.db ./bookserver
```

## Test
```sh
make test                  # builds and runs ./booktests against an in-memory SQLite DB
```

## Endpoints
| Method | Path | Description |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | Create a book → 201 |
| GET | /books[?author=Name] | List books, with an optional exact-match author filter |
| GET | /books/{id} | Get one book → 200 / 404 |
| PUT | /books/{id} | Replace a book → 200 / 404 |
| DELETE | /books/{id} | Delete a book → 204 / 404 |

Body: `{"title": "...", "author": "...", "year": 1965, "isbn": "..."}`. `title` and `author` are required and must be non-empty strings. `year` must be an integer if given, and `isbn` must be a string if given. Invalid input returns `400 {"error": "..."}`.

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank%20Herbert'
```

## Layout
- `BookStore.{h,m}`: SQLite persistence
- `BookAPI.{h,m}`: routing, validation and JSON responses (transport-independent)
- `main.m`: HTTP server
- `tests.m`: tests

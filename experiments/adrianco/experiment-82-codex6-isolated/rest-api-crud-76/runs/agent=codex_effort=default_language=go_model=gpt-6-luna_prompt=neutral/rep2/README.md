# Book Collection API

A small REST API written in Go using `net/http` and SQLite. The SQLite driver is pure Go, so no system SQLite installation is needed.

## Run

```sh
go run .
```

The server listens on `:8080` by default and creates `books.db` in the current directory. Set `ADDR` to change the listen address or `BOOKS_DB` to choose another SQLite database path. For example:

```sh
ADDR=:9000 BOOKS_DB=./library.db go run .
```

## Endpoints

- `GET /health` — database health status
- `POST /books` — create a book (`title`, `author` required; `year`, `isbn` optional)
- `GET /books` — list books; add `?author=Name` to filter by exact author
- `GET /books/{id}` — fetch one book
- `PUT /books/{id}` — replace a book's fields
- `DELETE /books/{id}` — delete a book

Book request example:

```json
{"title":"The Go Book","author":"Ada Lovelace","year":2024,"isbn":"9780000000000"}
```

Errors are JSON objects with an `error` field. Missing records return `404`, invalid input returns `400`, successful creation returns `201`, and successful deletion returns `204`.

## Test

```sh
go test ./...
```

# Book Collection API

REST API in Go (standard library `net/http`) backed by SQLite (pure-Go `modernc.org/sqlite`, no cgo).

## Run

    go run .                      # listens on :8080, database file books.db
    ADDR=:9000 DB_PATH=/tmp/b.db go run .

## Test

    go test ./...

## Endpoints

| Method | Path           | Description                          |
|--------|----------------|--------------------------------------|
| GET    | /health        | Health check                         |
| POST   | /books         | Create (`title`, `author` required)  |
| GET    | /books         | List; optional `?author=` filter     |
| GET    | /books/{id}    | Get one                              |
| PUT    | /books/{id}    | Update                               |
| DELETE | /books/{id}    | Delete (204)                         |

Book JSON: `{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"123"}`

Errors return `{"error":"..."}` with 400 (validation / bad id), 404 (not found) or 500.

    curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"123"}'

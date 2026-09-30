# Book Collection API

REST API for managing books, written in Go (stdlib `net/http`) with SQLite storage
via the pure-Go `modernc.org/sqlite` driver (no cgo required).

## Run

    go run .

Environment variables: `ADDR` (default `:8080`), `DB_PATH` (default `books.db`).

## Test

    go test ./...

## Endpoints

| Method | Path          | Description                          |
|--------|---------------|--------------------------------------|
| POST   | /books        | Create (title, author required)      |
| GET    | /books        | List; optional `?author=` exact filter |
| GET    | /books/{id}   | Get one                              |
| PUT    | /books/{id}   | Update                               |
| DELETE | /books/{id}   | Delete (204)                         |
| GET    | /health       | Health check                         |

Book JSON: `{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"123"}`

Errors return `{"error":"..."}` with 400 (validation), 404 (not found) or 500.

    curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"123"}'

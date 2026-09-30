# Book Collection API

REST API for managing books, written in Go using the standard library `net/http`
router and SQLite (pure-Go driver `modernc.org/sqlite`, no CGO required).

## Run

    go run .            # listens on :8080, database file books.db

Environment variables: `ADDR` (default `:8080`), `DB_PATH` (default `books.db`).

## Test

    go test ./...

## Endpoints

| Method | Path          | Description                                   |
|--------|---------------|-----------------------------------------------|
| GET    | /health       | Health check                                  |
| POST   | /books        | Create (`title`, `author` required; `year`, `isbn`) |
| GET    | /books        | List; optional `?author=` exact-match filter  |
| GET    | /books/{id}   | Get one                                       |
| PUT    | /books/{id}   | Replace/update                                |
| DELETE | /books/{id}   | Delete (204)                                  |

Errors return `{"error": "..."}` with 400 (validation), 404 (missing), or 500.

    curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# Book Collection API

REST API for managing books, written in Go (stdlib `net/http`) with SQLite via the pure-Go `modernc.org/sqlite` driver (no cgo needed).

## Run

    go run .

Environment variables: `ADDR` (default `:8080`), `DB_PATH` (default `books.db`).

## Test

    go test ./...

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | /health | Health check |
| POST | /books | Create (`title`, `author` required; `year`, `isbn`) → 201 |
| GET | /books | List; optional `?author=` exact-match filter |
| GET | /books/{id} | Get one (404 if missing) |
| PUT | /books/{id} | Replace/update (400 on invalid, 404 if missing) |
| DELETE | /books/{id} | Delete → 204 |

Example:

    curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
    curl 'localhost:8080/books?author=Frank%20Herbert'

Errors are returned as `{"error": "..."}`.

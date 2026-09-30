# Book Collection API

REST API for managing books, written in Go (standard library `net/http`) with SQLite storage (pure-Go `modernc.org/sqlite`, no CGO needed).

## Run

    go run .

Environment variables: `ADDR` (default `:8080`), `DB_PATH` (default `books.db`).

## Test

    go test ./...

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create (`title`, `author` required; `year`, `isbn` optional) → 201 |
| GET | `/books` | List; filter with `?author=Name` (exact match) |
| GET | `/books/{id}` | Get one → 200 / 404 |
| PUT | `/books/{id}` | Replace/update → 200 / 400 / 404 |
| DELETE | `/books/{id}` | Delete → 204 / 404 |

Errors are returned as `{"error": "..."}` with 400 (validation / bad id), 404, or 500.

Example:

    curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

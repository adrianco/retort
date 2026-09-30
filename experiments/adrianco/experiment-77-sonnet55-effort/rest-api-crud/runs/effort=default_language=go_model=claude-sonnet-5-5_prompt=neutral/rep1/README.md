# Book Collection API

REST API for managing books, written in Go (standard library `net/http`) with SQLite storage
via the pure-Go `modernc.org/sqlite` driver (no CGO required).

## Setup & run

Requires Go 1.22+.

    go mod download
    go run .

Environment variables: `ADDR` (default `:8080`), `DB_PATH` (default `books.db`).

## Test

    go test ./...

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/books` | Create a book (`title`, `author` required; `year`, `isbn` optional) → 201 |
| GET | `/books` | List books; optional `?author=` exact-match filter |
| GET | `/books/{id}` | Get one book (404 if missing) |
| PUT | `/books/{id}` | Replace a book (400 invalid, 404 missing) |
| DELETE | `/books/{id}` | Delete a book → 204 |
| GET | `/health` | Health check → `{"status":"ok"}` |

Errors are JSON: `{"error": "message"}`.

## Example

    curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
    curl 'localhost:8080/books?author=Frank%20Herbert'

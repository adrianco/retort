# Book Collection API

Go REST API (stdlib `net/http`) storing books in SQLite (pure-Go `modernc.org/sqlite`, no CGO).

## Run

    go run .            # listens on :8080, DB file books.db

Env vars: `ADDR` (default `:8080`), `DB_PATH` (default `books.db`).

## Test

    go test ./...

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | /health | Health check |
| POST | /books | Create (`title`, `author` required; `year`, `isbn`) → 201 |
| GET | /books | List; `?author=` filters (case-insensitive exact) |
| GET | /books/{id} | Get one → 200 / 404 |
| PUT | /books/{id} | Replace → 200 / 400 / 404 |
| DELETE | /books/{id} | Delete → 204 / 404 |

Example:

    curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# Book Collection API

Go REST API (stdlib `net/http`) storing books in SQLite (pure-Go `modernc.org/sqlite`, no CGO).

## Run

    go run .

Env vars: `ADDR` (default `:8080`), `DB_PATH` (default `books.db`).

## Test

    go test ./...

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | body: `title`*, `author`*, `year`, `isbn` → 201 |
| GET | /books | optional `?author=` exact-match filter |
| GET | /books/{id} | 404 if missing |
| PUT | /books/{id} | full update; 404 if missing |
| DELETE | /books/{id} | 204; 404 if missing |

Errors are JSON: `{"error":"..."}` (400 validation, 404 not found).

    curl -XPOST localhost:8080/books -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"123"}'

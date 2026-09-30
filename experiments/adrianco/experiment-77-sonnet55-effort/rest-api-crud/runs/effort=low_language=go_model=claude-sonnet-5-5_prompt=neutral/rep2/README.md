# Book Collection API

Go (stdlib `net/http`) REST service backed by SQLite (pure-Go `modernc.org/sqlite`, no CGO).

## Run
    go run .            # listens on :8080, DB file books.db
Env vars: `ADDR` (default `:8080`), `DB_PATH` (default `books.db`).

## Test
    go test ./...

## Endpoints
- `GET /health`
- `POST /books` — `{"title","author","year","isbn"}` (title, author required) → 201
- `GET /books[?author=Name]`
- `GET /books/{id}` → 200 / 404
- `PUT /books/{id}` → 200 / 400 / 404
- `DELETE /books/{id}` → 204 / 404

Errors are JSON: `{"error":"..."}`.

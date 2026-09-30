# Book Collection API

Go REST API (stdlib `net/http`) backed by SQLite (pure-Go `modernc.org/sqlite`, no cgo).

## Run

    go run .

Env vars: `ADDR` (default `:8080`), `DB_PATH` (default `books.db`).

## Test

    go test ./...

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | body `{title, author, year, isbn}`; title and author required; 201 |
| GET | /books | optional `?author=` exact-match filter |
| GET | /books/{id} | 404 if missing |
| PUT | /books/{id} | full update; 400 on validation, 404 if missing |
| DELETE | /books/{id} | 204; 404 if missing |

Errors are JSON: `{"error":"..."}`.

Example:

    curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

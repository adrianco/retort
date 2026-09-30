# Book Collection API

Go (stdlib `net/http`) REST API backed by SQLite (pure-Go `modernc.org/sqlite`, no cgo).

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
| PUT | /books/{id} | full update; 400 invalid, 404 missing |
| DELETE | /books/{id} | 204; 404 if missing |

Example:

    curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"123"}'

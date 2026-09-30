# Book Collection API

A REST API in Go (standard library `net/http`) storing books in SQLite via the pure-Go `modernc.org/sqlite` driver (no CGO needed).

## Run

    go run .

Environment: `ADDR` (default `:8080`), `DB_PATH` (default `books.db`).

## Test

    go test ./...

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /books | Create (`title`, `author` required; `year`, `isbn` optional) → 201 |
| GET | /books | List; optional `?author=Name` exact-match filter |
| GET | /books/{id} | Get one → 200 / 404 |
| PUT | /books/{id} | Replace/update → 200 / 400 / 404 |
| DELETE | /books/{id} | Delete → 204 / 404 |
| GET | /health | `{"status":"ok"}` |

Errors are JSON: `{"error":"..."}`.

    curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

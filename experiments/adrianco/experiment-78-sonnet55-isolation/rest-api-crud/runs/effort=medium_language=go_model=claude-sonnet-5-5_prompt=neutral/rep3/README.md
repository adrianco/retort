# Book Collection API

A REST API in Go (standard library `net/http`) storing books in SQLite (pure-Go `modernc.org/sqlite`, no CGO needed).

## Run

    go run .

Environment variables: `ADDR` (default `:8080`), `DB_PATH` (default `books.db`).

## Test

    go test ./...

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | /health | Health check |
| POST | /books | Create (`title`, `author` required; `year`, `isbn` optional) → 201 |
| GET | /books | List; optional `?author=` exact-match filter |
| GET | /books/{id} | Get one (404 if missing) |
| PUT | /books/{id} | Replace/update (400 on invalid, 404 if missing) |
| DELETE | /books/{id} | Delete → 204 |

Example:

    curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"123"}'

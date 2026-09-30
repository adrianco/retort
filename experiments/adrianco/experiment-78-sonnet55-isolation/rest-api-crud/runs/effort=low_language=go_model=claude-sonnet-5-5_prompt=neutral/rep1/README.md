# Book Collection API

Go (net/http) REST service backed by SQLite (pure-Go `modernc.org/sqlite`).

## Run
    go run .            # env: ADDR (default :8080), DB_PATH (default books.db)

## Test
    go test ./...

## Endpoints
- `GET /health`
- `POST /books` — `{"title","author","year","isbn"}` (title, author required) → 201
- `GET /books` — optional `?author=` exact-match filter
- `GET /books/{id}` — 200 / 404
- `PUT /books/{id}` — 200 / 400 / 404
- `DELETE /books/{id}` — 204 / 404

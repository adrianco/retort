# Book Collection API

Go (stdlib `net/http`) REST service backed by SQLite (pure-Go `modernc.org/sqlite`).

## Run
    go run .            # listens on :8080, DB file books.db
    ADDR=:9000 DB_PATH=/tmp/b.db go run .

## Test
    go test ./...

## Endpoints
- `POST /books` — body `{"title","author","year","isbn"}` (title, author required) → 201
- `GET /books` — list; optional `?author=NAME`
- `GET /books/{id}` — 200 or 404
- `PUT /books/{id}` — update → 200 / 400 / 404
- `DELETE /books/{id}` — 204 / 404
- `GET /health` — `{"status":"ok"}`

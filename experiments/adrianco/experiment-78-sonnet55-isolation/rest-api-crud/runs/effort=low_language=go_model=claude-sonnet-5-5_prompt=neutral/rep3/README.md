# Book Collection API

Go (stdlib `net/http`) REST API backed by SQLite (pure-Go `modernc.org/sqlite`, no cgo).

## Run
    go run .            # env: ADDR (default :8080), DB_PATH (default books.db)

## Test
    go test ./...

## Endpoints
- `POST /books` `{"title","author","year","isbn"}` — title and author required → 201
- `GET /books[?author=Name]` — list (exact author match)
- `GET /books/{id}` — 200 / 404
- `PUT /books/{id}` — 200 / 400 / 404
- `DELETE /books/{id}` — 204 / 404
- `GET /health` — `{"status":"ok"}`

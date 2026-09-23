# Book Collection API

REST API in Go (standard library `net/http` router) backed by SQLite (`modernc.org/sqlite`, pure Go, no cgo).

## Run

```sh
go mod download
go run .                       # listens on :8080, stores data in ./books.db
ADDR=:9000 DB_PATH=/tmp/b.db go run .
```

## Test

```sh
go test ./...
```

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | body `{"title","author","year","isbn"}`; title & author required → 201 |
| GET | /books | optional `?author=` (case-insensitive exact match) |
| GET | /books/{id} | 404 if missing |
| PUT | /books/{id} | full replace, same validation as POST |
| DELETE | /books/{id} | 204 on success |

Errors return `{"error": "..."}` with 400/404/500.

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
```

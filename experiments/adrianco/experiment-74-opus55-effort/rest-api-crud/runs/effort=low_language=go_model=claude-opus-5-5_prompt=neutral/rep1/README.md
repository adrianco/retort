# Book Collection API

REST API in Go (standard library `net/http`) backed by SQLite (`modernc.org/sqlite`, pure Go, no CGO).

## Run

```sh
go run .                          # listens on :8080, stores data in ./books.db
ADDR=:9000 DB_PATH=/tmp/b.db go run .
```

## Test

```sh
go test ./...
```

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | /health | Health check |
| POST | /books | Create book (`title`, `author` required; `year`, `isbn` optional) → 201 |
| GET | /books?author= | List books, optional case-insensitive exact author filter |
| GET | /books/{id} | Get book → 200 / 404 |
| PUT | /books/{id} | Replace book → 200 / 400 / 404 |
| DELETE | /books/{id} | Delete book → 204 / 404 |

Example:

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

Validation errors return 400 with `{"error":"validation failed","fields":{...}}`.

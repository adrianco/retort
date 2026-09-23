# Book Collection API (Go)

REST API for a book collection using Go's standard `net/http` router and SQLite (`modernc.org/sqlite`, pure Go, no CGO).

## Run

```sh
go mod download
go run .            # listens on :8080, stores data in ./books.db
PORT=9000 DB_PATH=/tmp/books.db go run .
```

## Test

```sh
go test -v ./...
```

## Endpoints

| Method | Path | Description | Success |
|---|---|---|---|
| GET | /health | Health check | 200 |
| POST | /books | Create book (`title`, `author` required; `year`, `isbn` optional) | 201 |
| GET | /books[?author=] | List books, optional case-insensitive author filter | 200 |
| GET | /books/{id} | Get book | 200 / 404 |
| PUT | /books/{id} | Replace book (same validation as create) | 200 / 404 |
| DELETE | /books/{id} | Delete book | 204 / 404 |

Validation errors return 400 with `{"error": "...", "details": [...]}`.

```sh
curl -X POST localhost:8080/books -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

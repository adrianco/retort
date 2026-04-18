# Book API

A REST API for managing a book collection, written in Go using the standard library `net/http` and an embedded SQLite database (`modernc.org/sqlite`, pure Go — no CGO required).

## Requirements

- Go 1.21+

## Setup & Run

```bash
go mod tidy
go run .
```

The server listens on `:8080` by default. Override with env vars:

- `ADDR` — listen address (e.g. `:9000`)
- `DB_PATH` — path to SQLite file (default: `books.db`)

## Endpoints

| Method | Path            | Description                        |
|--------|-----------------|------------------------------------|
| GET    | `/health`       | Health check                       |
| POST   | `/books`        | Create a book                      |
| GET    | `/books`        | List books (optional `?author=`)   |
| GET    | `/books/{id}`   | Get a book by ID                   |
| PUT    | `/books/{id}`   | Update a book                      |
| DELETE | `/books/{id}`   | Delete a book                      |

### Book JSON shape

```json
{ "id": 1, "title": "Dune", "author": "Herbert", "year": 1965, "isbn": "..." }
```

`title` and `author` are required on create and update.

### Example

```bash
curl -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"0441172717"}'

curl localhost:8080/books
curl 'localhost:8080/books?author=Herbert'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -X DELETE localhost:8080/books/1
```

## Tests

```bash
go test ./...
```

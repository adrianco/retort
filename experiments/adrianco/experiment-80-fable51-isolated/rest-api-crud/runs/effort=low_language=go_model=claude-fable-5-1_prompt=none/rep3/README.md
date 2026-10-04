# Book Collection API

A REST API for managing a book collection, written in Go using the standard
library `net/http` router and SQLite (via the pure-Go `modernc.org/sqlite`
driver — no CGO required).

## Setup

Requires Go 1.22+.

```bash
go mod download
```

## Run

```bash
go run .
```

Configuration via environment variables:

| Variable  | Default    | Description               |
|-----------|------------|---------------------------|
| `PORT`    | `8080`     | HTTP listen port          |
| `DB_PATH` | `books.db` | SQLite database file path |

## Test

```bash
go test ./...
```

## Endpoints

| Method | Path          | Description                              | Success |
|--------|---------------|------------------------------------------|---------|
| GET    | `/health`     | Health check                             | 200     |
| POST   | `/books`      | Create a book                            | 201     |
| GET    | `/books`      | List books (optional `?author=` filter)  | 200     |
| GET    | `/books/{id}` | Get a book                               | 200     |
| PUT    | `/books/{id}` | Update (replace) a book                  | 200     |
| DELETE | `/books/{id}` | Delete a book                            | 204     |

Book JSON: `{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}`

`title` and `author` are required; invalid input returns `400`, unknown IDs
return `404`. Errors are returned as `{"error": "message"}`.

## Example

```bash
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:8080/books?author=Frank+Herbert'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:8080/books/1
```

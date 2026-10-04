# Book Collection API

A REST API for managing a book collection, written in Go with the standard
library `net/http` router and SQLite (via the pure-Go `modernc.org/sqlite`
driver, so no CGO is needed).

## Setup

Requires Go 1.22+.

```bash
go mod download
go build -o books-api .
```

## Run

```bash
./books-api          # or: go run .
```

Configuration via environment variables:

| Variable  | Default    | Description               |
|-----------|------------|---------------------------|
| `PORT`    | `8080`     | HTTP listen port          |
| `DB_PATH` | `books.db` | SQLite database file path |

## Endpoints

| Method | Path          | Description                          | Success |
|--------|---------------|--------------------------------------|---------|
| GET    | `/health`     | Health check                         | 200     |
| POST   | `/books`      | Create a book                        | 201     |
| GET    | `/books`      | List books (optional `?author=`)     | 200     |
| GET    | `/books/{id}` | Get one book                         | 200     |
| PUT    | `/books/{id}` | Update a book (full replacement)     | 200     |
| DELETE | `/books/{id}` | Delete a book                        | 204     |

Book JSON: `{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}`

`title` and `author` are required; invalid input returns `400`, unknown IDs
return `404`. Errors are returned as `{"error": "message"}`.

## Example

```bash
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
curl 'localhost:8080/books?author=Frank+Herbert'
```

## Tests

```bash
go test ./...
```

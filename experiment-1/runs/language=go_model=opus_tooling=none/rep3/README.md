# Books API

REST API for managing a book collection, written in Go with SQLite (pure-Go `modernc.org/sqlite`, no CGO required).

## Setup

```bash
go mod tidy
go build ./...
```

## Run

```bash
go run .
```

Environment variables:
- `PORT` — listen port (default `8080`)
- `DB_PATH` — SQLite file (default `books.db`)

## Test

```bash
go test ./...
```

## Endpoints

| Method | Path           | Description                         |
|--------|----------------|-------------------------------------|
| GET    | /health        | Health check                        |
| POST   | /books         | Create a book                       |
| GET    | /books         | List books (supports `?author=...`) |
| GET    | /books/{id}    | Get a book                          |
| PUT    | /books/{id}    | Update a book                       |
| DELETE | /books/{id}    | Delete a book                       |

Book JSON: `{"title": "...", "author": "...", "year": 2020, "isbn": "..."}`. `title` and `author` are required.

## Example

```bash
curl -X POST localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Donovan","year":2015,"isbn":"978-0134190440"}'
curl localhost:8080/books
curl 'localhost:8080/books?author=Donovan'
```

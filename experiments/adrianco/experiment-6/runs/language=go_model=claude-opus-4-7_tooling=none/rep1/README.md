# Book API

A small REST service for managing a book collection, written in Go with the
`net/http` standard library router (Go 1.22+) and an embedded SQLite database
(`modernc.org/sqlite`, pure-Go — no CGO required).

## Requirements

- Go 1.22 or newer

## Setup

```sh
go mod download
```

## Run

```sh
go run .
```

The server listens on `:8080` and stores data in `books.db` in the working
directory. Override with environment variables:

- `BOOKS_ADDR` — listen address (default `:8080`)
- `BOOKS_DB`   — SQLite DSN / file path (default `books.db`)

## Test

```sh
go test ./...
```

## Endpoints

| Method | Path           | Description                              |
| ------ | -------------- | ---------------------------------------- |
| GET    | `/health`      | Health check — returns `{"status":"ok"}` |
| POST   | `/books`       | Create a book                            |
| GET    | `/books`       | List books (optional `?author=` filter)  |
| GET    | `/books/{id}`  | Get a single book by ID                  |
| PUT    | `/books/{id}`  | Update a book                            |
| DELETE | `/books/{id}`  | Delete a book                            |

### Book payload

```json
{
  "title": "The Go Programming Language",
  "author": "Alan Donovan",
  "year": 2015,
  "isbn": "978-0134190440"
}
```

`title` and `author` are required; missing/blank values produce HTTP 400 with an
`errors` array.

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — invalid JSON or failed validation
- `404 Not Found` — unknown book id
- `500 Internal Server Error` — unexpected database error

## Example

```sh
# create
curl -s -X POST localhost:8080/books \
  -H 'content-type: application/json' \
  -d '{"title":"Go","author":"Donovan","year":2015,"isbn":"x"}'

# list, filter by author
curl -s 'localhost:8080/books?author=Donovan'

# update
curl -s -X PUT localhost:8080/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Go 2e","author":"Donovan","year":2024,"isbn":"y"}'

# delete
curl -s -X DELETE localhost:8080/books/1 -i
```

## Layout

- `main.go`      — entry point, env config, server start
- `book.go`      — `Book` model and input validation
- `store.go`     — SQLite-backed CRUD store
- `handlers.go`  — HTTP handlers and routing
- `handlers_test.go` — integration tests covering health, create+get,
  validation, author filter, update+delete, and not-found

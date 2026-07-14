# Books API

A small REST API for managing a book collection, written in Go with SQLite (via `modernc.org/sqlite`, pure-Go — no CGO required).

## Requirements

- Go 1.25+ (no CGO needed)

## Setup

```sh
go mod tidy
go build ./...
```

## Run

```sh
go run .
```

Environment variables:

- `ADDR` — listen address (default `:8080`)
- `DB_PATH` — SQLite file path (default `books.db`)

## Endpoints

| Method | Path           | Description                               |
| ------ | -------------- | ----------------------------------------- |
| GET    | `/health`      | Health check                              |
| POST   | `/books`       | Create a book (`title`, `author` required)|
| GET    | `/books`       | List books, optional `?author=` filter    |
| GET    | `/books/{id}`  | Get a book by ID                          |
| PUT    | `/books/{id}`  | Update a book                             |
| DELETE | `/books/{id}`  | Delete a book                             |

Book JSON shape:

```json
{ "id": 1, "title": "Go", "author": "Alan", "year": 2020, "isbn": "123" }
```

## Example

```sh
curl -X POST localhost:8080/books \
  -H 'content-type: application/json' \
  -d '{"title":"Go","author":"Alan","year":2020,"isbn":"123"}'

curl localhost:8080/books
curl 'localhost:8080/books?author=Alan'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Go 2e","author":"Alan","year":2024,"isbn":"123"}'
curl -X DELETE localhost:8080/books/1
```

## Tests

```sh
go test ./...
```

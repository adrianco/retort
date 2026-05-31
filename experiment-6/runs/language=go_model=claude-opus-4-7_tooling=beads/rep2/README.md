# Books REST API

A small REST API for managing a book collection. Written in Go with SQLite
storage (via the pure-Go `modernc.org/sqlite` driver, so no CGo is required).

## Requirements

- Go 1.22+ (uses the method-aware `net/http` routing patterns)

## Setup

Fetch dependencies:

```sh
go mod download
```

## Build

```sh
go build -o books .
```

## Run

```sh
./books                                # listens on :8080, db file books.db
./books -addr :9090 -db /tmp/books.db  # custom address and database path
ADDR=:9090 DB_PATH=/tmp/books.db ./books
```

Or directly:

```sh
go run .
```

## Test

```sh
go test ./...
```

There are five tests covering the health endpoint, create/get, validation,
listing with the `?author=` filter, and update/delete.

## API

All requests and responses are JSON. A book has the following shape:

```json
{ "id": 1, "title": "...", "author": "...", "year": 2020, "isbn": "..." }
```

| Method | Path           | Description                              | Success status |
| ------ | -------------- | ---------------------------------------- | -------------- |
| GET    | `/health`      | Liveness check                           | 200            |
| GET    | `/books`       | List books; optional `?author=` filter   | 200            |
| POST   | `/books`       | Create a book (`title`, `author` required) | 201           |
| GET    | `/books/{id}`  | Fetch a book by id                       | 200            |
| PUT    | `/books/{id}`  | Replace a book                           | 200            |
| DELETE | `/books/{id}`  | Remove a book                            | 204            |

Error responses use the shape `{ "error": "..." }` with status codes:

- `400 Bad Request` — invalid JSON, missing `title` or `author`, malformed id
- `404 Not Found` — no such book
- `500 Internal Server Error` — unexpected storage error

### Examples

```sh
# Create
curl -sX POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Donovan","year":2015,"isbn":"9780134190440"}'

# List
curl -s localhost:8080/books
curl -s 'localhost:8080/books?author=Donovan'

# Get
curl -s localhost:8080/books/1

# Update
curl -sX PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Donovan & Kernighan","year":2015,"isbn":"9780134190440"}'

# Delete
curl -sX DELETE localhost:8080/books/1
```

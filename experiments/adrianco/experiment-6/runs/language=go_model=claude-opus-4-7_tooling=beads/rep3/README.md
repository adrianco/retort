# Book API

A small REST service for managing a book collection, written in Go using the
standard library `net/http` and SQLite (via the pure-Go
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) driver — no CGO
required).

## Requirements

- Go 1.22+

## Setup

```sh
go mod download
```

## Run

```sh
go run .
```

The server listens on `:8080` by default and persists data to `books.db` in
the working directory. Both can be overridden with env vars:

```sh
BOOKS_ADDR=:9090 BOOKS_DB=/tmp/library.db go run .
```

## Test

```sh
go test ./...
```

## Endpoints

| Method | Path           | Description                                   |
| ------ | -------------- | --------------------------------------------- |
| GET    | `/health`      | Health check — returns `{"status":"ok"}`      |
| POST   | `/books`       | Create a book                                 |
| GET    | `/books`       | List books; optional `?author=<name>` filter  |
| GET    | `/books/{id}`  | Fetch a book by ID                            |
| PUT    | `/books/{id}`  | Replace a book                                |
| DELETE | `/books/{id}`  | Delete a book                                 |

### Book schema

```json
{
  "id": 1,
  "title": "The Pragmatic Programmer",
  "author": "Hunt",
  "year": 1999,
  "isbn": "978-0201616224"
}
```

`title` and `author` are required on POST and PUT (whitespace-only strings are
rejected with `400 Bad Request`).

### Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — invalid JSON or missing required fields
- `404 Not Found` — unknown book ID
- `405 Method Not Allowed` — unsupported HTTP method for the route
- `500 Internal Server Error` — unexpected storage failure

## Examples

```sh
# Create
curl -s -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"978-0441172719"}'

# List, filtered by author
curl -s 'http://localhost:8080/books?author=Herbert'

# Get one
curl -s http://localhost:8080/books/1

# Update
curl -s -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

# Delete
curl -s -X DELETE http://localhost:8080/books/1 -o /dev/null -w '%{http_code}\n'
```

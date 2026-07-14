# Book Collection API

A REST API for managing a book collection, built with Go and SQLite.

## Requirements

- Go 1.21+
- gcc (required by `go-sqlite3` for CGO)

## Setup

```bash
go mod download
```

## Run

```bash
go run .
```

The server listens on `:8080` by default. Override with environment variables:

| Variable | Default     | Description          |
|----------|-------------|----------------------|
| `ADDR`   | `:8080`     | Listen address       |
| `DB_PATH`| `books.db`  | SQLite database path |

```bash
ADDR=:9090 DB_PATH=/tmp/books.db go run .
```

## API

### Health check

```
GET /health
```

### Create a book

```
POST /books
Content-Type: application/json

{"title": "The Go Programming Language", "author": "Alan Donovan", "year": 2015, "isbn": "978-0134190440"}
```

Returns `201 Created` with the created book (including assigned `id`).

`title` and `author` are required. `year` and `isbn` are optional.

### List books

```
GET /books
GET /books?author=Alan+Donovan
```

Returns `200 OK` with a JSON array of books. Use the optional `?author=` query parameter to filter.

### Get a book

```
GET /books/{id}
```

Returns `200 OK` with the book, or `404 Not Found`.

### Update a book

```
PUT /books/{id}
Content-Type: application/json

{"title": "Updated Title", "author": "Author Name"}
```

Returns `200 OK` with the updated book, or `404 Not Found`.

### Delete a book

```
DELETE /books/{id}
```

Returns `204 No Content`, or `404 Not Found`.

## Tests

```bash
go test ./...
```

# Books API

A REST API for managing a book collection, written in Go with SQLite storage.

## Requirements

- Go 1.22+

## Setup

```bash
go mod download
```

## Run

```bash
go run .
```

The server listens on port `8080` by default. Override with the `PORT` environment variable. The SQLite database is stored in `books.db` by default; override with `DATABASE_URL`.

```bash
PORT=9000 DATABASE_URL=/tmp/mybooks.db go run .
```

## API

### Health check

```
GET /health
```

### Books

| Method | Path | Description |
|--------|------|-------------|
| POST | /books | Create a book |
| GET | /books | List all books |
| GET | /books?author=Name | Filter by author |
| GET | /books/{id} | Get a book |
| PUT | /books/{id} | Update a book |
| DELETE | /books/{id} | Delete a book |

#### Book fields

| Field | Type | Required |
|-------|------|----------|
| title | string | yes |
| author | string | yes |
| year | int | no |
| isbn | string | no |

#### Examples

```bash
# Create
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Alan Donovan","year":2015}'

# List
curl http://localhost:8080/books

# Filter by author
curl 'http://localhost:8080/books?author=Alan+Donovan'

# Get by ID
curl http://localhost:8080/books/1

# Update
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Updated Title","author":"Alan Donovan","year":2016}'

# Delete
curl -X DELETE http://localhost:8080/books/1
```

## Tests

```bash
go test ./...
```

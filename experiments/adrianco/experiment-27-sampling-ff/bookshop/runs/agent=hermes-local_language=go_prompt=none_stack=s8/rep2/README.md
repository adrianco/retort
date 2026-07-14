# Book API REST Service

A Go-based REST API for managing a book collection, backed by SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update an existing book
- **DELETE /books/{id}** — Delete a book by ID
- **GET /health** — Health check endpoint

## Prerequisites

- Go 1.26 or later
- GCC (required by `github.com/mattn/go-sqlite3` CGo)

## Setup and Run

```bash
# Download dependencies
go mod tidy

# Run the server
go run app.go
```

The API will be available at `http://localhost:8080`.

## Testing

```bash
go test -v
```

## API Examples

### Create a book

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language","author":"Donovan & Kernighan","year":2015,"isbn":"978-0134190440"}'
```

### List all books

```bash
curl http://localhost:8080/books
```

### List books by author

```bash
curl "http://localhost:8080/books?author=Robert+C.+Martin"
```

### Get a single book

```bash
curl http://localhost:8080/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title","year":2025}'
```

### Delete a book

```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check

```bash
curl http://localhost:8080/health
```

## Data Model

| Field | Type   | Required | Description          |
|-------|--------|----------|----------------------|
| id    | int    | Yes (auto)   | Auto-incrementing primary key |
| title | string | Yes    | Book title           |
| author| string | Yes    | Author name          |
| year  | int    | No     | Publication year     |
| isbn  | string | No     | ISBN number          |

## Response Codes

- `201 Created` — Book successfully created
- `200 OK` — Successful GET/PUT/DELETE
- `400 Bad Request` — Invalid input or missing required fields
- `404 Not Found` — Book not found
- `500 Internal Server Error` — Database error

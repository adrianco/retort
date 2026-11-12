# Book API

A REST API service for managing a book collection, built in Go with SQLite.

## Endpoints

- `POST /books` — Create a new book (body: `title`, `author`, `year`, `isbn`)
- `GET /books` — List all books (supports `?author=` query filter)
- `GET /books/{id}` — Get a single book by ID
- `PUT /books/{id}` — Update a book
- `DELETE /books/{id}` — Delete a book
- `GET /health` — Health check

## Setup

1. Install Go 1.21 or later.
2. Clone or copy the source into a Go workspace.
3. Download dependencies:

```bash
go mod download
```

## Run

```bash
go run .
```

The server listens on `:8080` by default. Use `-addr` to change the address:

```bash
go run . -addr :3000
```

## Build

```bash
go build -o bookapi .
./bookapi
```

## Tests

```bash
go test -v ./...
```

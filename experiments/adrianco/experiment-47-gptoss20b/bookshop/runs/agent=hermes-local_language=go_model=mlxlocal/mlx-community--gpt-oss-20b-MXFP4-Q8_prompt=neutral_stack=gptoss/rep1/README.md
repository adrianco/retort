# Book Collection REST API

## Overview

This is a simple REST API written in Go that lets you manage a collection of books. It supports creating, reading, updating, and deleting books, as well as listing all books with an optional author filter. The data is persisted in a SQLite database.

## Features

- **CRUD** for books (`POST /books`, `GET /books`, `GET /books/{id}`, `PUT /books/{id}`, `DELETE /books/{id}`)
- **Author filter** on the list endpoint (`GET /books?author=…`)
- **Health check** (`GET /health`)
- JSON responses with appropriate HTTP status codes
- Input validation – title and author are required
- Uses an embedded SQLite database (file `books.db` in the working directory)

## Prerequisites

- Go 1.22 or newer
- SQLite (included via the `github.com/mattn/go-sqlite3` driver)

## Setup & Run

```bash
# Clone the repository
git clone <repo-url>
cd <repo-dir>

# Install dependencies
go mod download

# Build the binary
go build -o bookapi

# Run the server
./bookapi
```

The server listens on port `8080`.

## API Endpoints

| Method | Path                | Description |
|--------|---------------------|-------------|
| POST   | `/books`            | Create a new book. Body must include `title`, `author`, `year`, `isbn`. Returns `201` with the created book.
| GET    | `/books`            | List all books. Supports optional query `?author=`.
| GET    | `/books/{id}`       | Retrieve a single book by ID. Returns `200` or `404`.
| PUT    | `/books/{id}`       | Update an existing book. Body must include `title` and `author`. Returns `200` or `404`.
| DELETE | `/books/{id}`       | Delete a book. Returns `204` or `404`.
| GET    | `/health`           | Health‑check endpoint. Returns JSON `{"status":"ok"}`.

## Testing

Run the unit/integration tests with:

```bash
go test ./...
```

The test suite contains three integration tests covering creation, retrieval, list filtering, and the health endpoint.

## License

MIT License.

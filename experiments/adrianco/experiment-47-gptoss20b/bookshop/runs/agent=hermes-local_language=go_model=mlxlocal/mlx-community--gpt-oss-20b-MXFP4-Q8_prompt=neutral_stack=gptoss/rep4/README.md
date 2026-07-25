# Book API Service

This repository contains a simple REST API for managing a book collection.

## Features

* Create, read, update, and delete books.
* List all books with optional author filtering.
* SQLite persistence.
* Health‑check endpoint.
* Input validation – title and author are required.

## Requirements

* Go 1.22 or newer.
* SQLite3 driver (bundled via `github.com/mattn/go-sqlite3`).

## Setup & Run

```bash
# Clone the repository
git clone <repo-url>
cd <repo-dir>

# Build the binary
go build -o bookapi .

# Run the server (listens on :8080)
./bookapi
```

The API is now available at `http://localhost:8080`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health‑check. Returns `200 OK`.
| POST | `/books` | Create a book. Body JSON: `{"title":..., "author":..., "year":..., "isbn":...}`.
| GET | `/books` | List all books. Optional query `?author=`.
| GET | `/books/{id}` | Get a single book by ID.
| PUT | `/books/{id}` | Update a book. Body JSON similar to POST.
| DELETE | `/books/{id}` | Delete a book.

All JSON responses use appropriate status codes (201 for create, 200 for success, 404 for not found, 400 for bad request, etc.).

## Tests

Run the unit and integration tests with:

```bash
go test ./...
```

Three test suites cover health, CRUD operations, filtering, and validation.

---

Happy coding!
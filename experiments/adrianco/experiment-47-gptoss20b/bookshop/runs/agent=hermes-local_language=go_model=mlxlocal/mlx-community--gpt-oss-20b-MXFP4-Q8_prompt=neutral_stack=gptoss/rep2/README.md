# Book API

A simple REST API for managing a book collection.

## Requirements

- Go 1.20 or later
- Git

## Setup

```bash
# Clone the repo (or copy the files into a folder)
# Install dependencies
go mod tidy

# Run the server
go run main.go

# The API listens on :8080
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST   | /books | Create a new book (JSON body with title, author, year, isbn). Title and author are required. |
| GET    | /books | List all books. Optional query `?author=` filters by author. |
| GET    | /books/{id} | Retrieve a single book by ID. |
| PUT    | /books/{id} | Update a book. Body must contain title and author. |
| DELETE | /books/{id} | Delete a book. |
| GET    | /health | Health‑check endpoint. Returns `{"status":"ok"}`. |

## Tests

Run tests with:

```bash
go test ./...
```

The test suite verifies creation, retrieval, listing, filtering, updating, deletion, and health‑check functionality.

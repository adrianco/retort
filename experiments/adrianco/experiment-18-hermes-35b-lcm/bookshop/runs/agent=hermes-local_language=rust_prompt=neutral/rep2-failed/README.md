# Book API REST Service

A REST API service for managing a book collection, built with Rust, actix-web, and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Technical Details

- **Framework**: actix-web 4
- **Database**: SQLite (in-memory via rusqlite, backed by bundled libsqlite3)
- **Serialization**: serde + serde_json
- **Language**: Rust 2021 edition

## Setup and Run

### Prerequisites

- Rust 1.70+ (installed via [rustup](https://rustup.rs/))
- Cargo (comes with Rust)

### Building

```bash
cargo build
```

### Running

```bash
cargo run
```

The server starts on `http://0.0.0.0:8080`.

### Testing

```bash
cargo test
```

The test suite covers:
- Creating books (valid and invalid input)
- Listing all books and filtering by author
- Getting a single book by ID (including not found)
- Updating a book
- Deleting a book
- Health check endpoint
- Full CRUD workflow

### Usage Examples

```bash
# Create a book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Rust Programming Language", "author": "Steve Klabnik", "year": 2023, "isbn": "978-1-7185-0044-0"}'

# List all books
curl http://localhost:8080/books

# Filter books by author
curl "http://localhost:8080/books?author=Steve%20Klabnik"

# Get a single book
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Rust Programming Language (2nd Edition)", "author": "Steve Klabnik", "year": 2025, "isbn": "978-1-7185-0305-2"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1

# Health check
curl http://localhost:8080/health
```

## Project Structure

```
├── Cargo.toml           # Project dependencies
├── README.md            # This file
└── src/
    ├── main.rs          # HTTP routes, handlers, and tests
    ├── models.rs        # Data models and validation logic
    └── db.rs            # SQLite database layer (in-memory)
```

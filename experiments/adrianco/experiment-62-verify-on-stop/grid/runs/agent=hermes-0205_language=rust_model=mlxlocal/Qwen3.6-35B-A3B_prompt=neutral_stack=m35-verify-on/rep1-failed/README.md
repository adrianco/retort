# Book API

A REST API service for managing a book collection, built with Rust.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (supports ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Technical Details

- Language: Rust (Edition 2021)
- Web Framework: actix-web 4
- Database: SQLite (via rusqlite with bundled driver)
- Data format: JSON
- Storage: In-memory SQLite database

## Prerequisites

- Rust 1.70+ (rustc)
- Cargo (Rust package manager)
- A C compiler (for building the bundled SQLite driver)

## Setup and Run

1. Clone or navigate to the project directory:

```bash
cd book-api
```

2. Build the project:

```bash
cargo build
```

3. Run the server:

```bash
cargo run
```

The server will start on http://127.0.0.1:8080

## API Examples

Create a book:
```bash
curl -X POST http://127.0.0.1:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949}'
```

List all books:
```bash
curl http://127.0.0.1:8080/books
```

List books by author:
```bash
curl "http://127.0.0.1:8080/books?author=Orwell"
```

Get a book by ID:
```bash
curl http://127.0.0.1:8080/books/<book-id>
```

Update a book:
```bash
curl -X PUT http://127.0.0.1:8080/books/<book-id> \
  -H "Content-Type: application/json" \
  -d '{"title": "1984 - Updated Edition"}'
```

Delete a book:
```bash
curl -X DELETE http://127.0.0.1:8080/books/<book-id>
```

Health check:
```bash
curl http://127.0.0.1:8080/health
```

## Validation

- title and author are required fields (return 400 if missing or empty)
- All responses are in JSON format
- Appropriate HTTP status codes are returned:
  - 200: Success
  - 201: Created
  - 204: No Content (delete success)
  - 400: Bad Request (validation error)
  - 404: Not Found

## Running Tests

Run all tests (unit + integration):

```bash
cargo test
```

This runs 21 tests covering:
- Database layer: create, read, update, delete, list, filter, validation
- HTTP endpoints: health check, create, list, get, update, delete with proper status codes

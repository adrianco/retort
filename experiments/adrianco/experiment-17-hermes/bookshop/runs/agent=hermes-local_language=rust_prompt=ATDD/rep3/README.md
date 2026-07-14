# Book API Service

A REST API service for managing a book collection.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint

## Endpoints

- `GET /health` - Health check
- `POST /books` - Create a new book
- `GET /books` - List all books (with optional author filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book

## Requirements

- Rust 1.56 or later
- Cargo

## Setup

```bash
cargo run
```

The API will be available at http://127.0.0.1:8080

## Tests

To run tests:
```bash
cargo test
```

## Acceptance Tests

This service implements the following executable acceptance tests:

1. Health check endpoint works
2. Book creation with valid data succeeds
3. Book listing works with filtering by author
4. Getting a specific book by ID works
5. Updating a book works
6. Deleting a book works
7. Input validation works (required fields)
8. Full CRUD cycle works correctly

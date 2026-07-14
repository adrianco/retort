# Book API REST Service

A REST API service for managing a book collection built with Rust and Actix Web.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- SQLite database storage
- Input validation

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (with optional `?author=` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Requirements

- Rust 1.56 or later
- Cargo

## Setup

1. Clone the repository
2. Navigate to the project directory
3. Build the project:

```bash
cargo build
```

## Running

To run the server:

```bash
cargo run
```

The server will start on `http://127.0.0.1:8080`.

## Testing

To run tests:

```bash
cargo test
```

## Example Usage

### Create a book
```bash
curl -X POST http://127.0.0.1:8080/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Rust Programming Language",
    "author": "Steve Klabnik",
    "year": 2018,
    "isbn": "978-0998741004"
  }'
```

### Get all books
```bash
curl http://127.0.0.1:8080/books
```

### Get books by author
```bash
curl http://127.0.0.1:8080/books?author=Steve%20Klabnik
```

### Get a specific book
```bash
curl http://127.0.0.1:8080/books/{id}
```

### Update a book
```bash
curl -X PUT http://127.0.0.1:8080/books/{id} \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Rust Programming Language - Second Edition",
    "author": "Steve Klabnik",
    "year": 2020,
    "isbn": "978-0998741004"
  }'
```

### Delete a book
```bash
curl -X DELETE http://127.0.0.1:8080/books/{id}
```

### Health check
```bash
curl http://127.0.0.1:8080/health
```

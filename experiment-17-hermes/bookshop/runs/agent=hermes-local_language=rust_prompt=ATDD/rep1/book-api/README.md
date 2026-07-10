# Book API

A REST API service for managing a book collection built with Rust and Warp.

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

1. Clone this repository
2. Navigate to the project directory
3. Build the project: `cargo build`
4. Run the server: `cargo run`

## Testing

Run tests with: `cargo test`

## Example Usage

### Create a book
```bash
curl -X POST http://localhost:3030/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'
```

### Get all books
```bash
curl http://localhost:3030/books
```

### Get books by author
```bash
curl http://localhost:3030/books?author=F. Scott Fitzgerald
```

### Get a single book
```bash
curl http://localhost:3030/books/<BOOK_ID>
```

### Update a book
```bash
curl -X PUT http://localhost:3030/books/<BOOK_ID> \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3030/books/<BOOK_ID>
```

### Health check
```bash
curl http://localhost:3030/health
```

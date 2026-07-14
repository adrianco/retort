# Book API Service

A REST API service for managing a book collection, implemented in Rust with Actix Web.

## Features

- POST /books - Create a new book
- GET /books - List all books (supports ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Requirements

- Rust 1.56 or later
- Cargo

## Setup

1. Clone this repository
2. Navigate to the project directory
3. Build the project:

```bash
cargo build
```

## Running

```bash
cargo run
```

The service will start on `http://127.0.0.1:8080`.

## API Endpoints

### Health Check
```http
GET /health
```

### Create Book
```http
POST /books
Content-Type: application/json

{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
}
```

### List Books
```http
GET /books
```

### Get Book by ID
```http
GET /books/{id}
```

### Update Book
```http
PUT /books/{id}
Content-Type: application/json

{
    "title": "The Great Gatsby - Updated",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
}
```

### Delete Book
```http
DELETE /books/{id}
```

## Testing

Run the tests with:

```bash
cargo test
```

## Implementation Details

This implementation uses in-memory storage for books. It's designed to be simple and demonstrate the core functionality without external dependencies like a database. For production use, you would want to integrate with a proper database system.

The implementation includes:
- Input validation for required fields (title and author)
- Proper HTTP status codes
- JSON responses
- All required endpoints as specified in the task
# Book Collection REST API

A REST API service for managing a book collection with SQLite storage.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (with optional `?author=` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Setup and Run

1. Install Rust (if not already installed)
2. Run the application:
   ```
   cargo run
   ```

3. The service will start on `http://localhost:8080`

## Testing

Run the tests with:
```
cargo test
```

## Requirements

- Rust 1.70+
- Cargo
- SQLite (embedded)

## Implementation Details

- Uses SQLite for data persistence
- JSON request/response format
- HTTP status codes appropriate to the operation
- Input validation for required fields
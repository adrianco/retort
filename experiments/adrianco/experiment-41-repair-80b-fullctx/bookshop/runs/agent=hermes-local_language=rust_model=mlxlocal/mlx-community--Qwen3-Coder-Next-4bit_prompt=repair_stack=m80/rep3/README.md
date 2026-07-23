# Book API REST Service

A REST API service for managing a book collection built with Rust, Actix Web, and SQLite.

## Features

- POST /books - Create a new book
- GET /books - List all books (supports ?author filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Prerequisites

- Rust 1.70 or later
- Cargo (comes with Rust)

## Setup

1. Clone the repository (or navigate to the project directory)

2. Build the project:
```bash
cargo build --release
```

3. Run the server:
```bash
cargo run --release
```

The server will start on `http://127.0.0.1:8080`

## API Usage

### Create a Book

```bash
curl -X POST http://127.0.0.1:8080/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
  }'
```

### Get All Books

```bash
curl http://127.0.0.1:8080/books
```

### Filter Books by Author

```bash
curl "http://127.0.0.1:8080/books?author=Author%20Name"
```

### Get a Single Book

```bash
curl http://127.0.0.1:8080/books/1
```

### Update a Book

```bash
curl -X PUT http://127.0.0.1:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "year": 1926
  }'
```

### Delete a Book

```bash
curl -X DELETE http://127.0.0.1:8080/books/1
```

### Health Check

```bash
curl http://127.0.0.1:8080/health
```

## Testing

Run the test suite:

```bash
cargo test
```

## Project Structure

```
src/
├── lib.rs          # Library module with exports
├── main.rs         # Application entry point
├── api.rs          # API endpoints and handlers
└── repository.rs   # Database repository and CRUD operations
```

## Dependencies

- `actix-web` - Web framework
- `sqlx` - Async SQL database library
- `serde` - Serialization/deserialization
- `validator` - Input validation
- `thiserror` - Error handling
- `uuid` - UUID generation

## License

MIT

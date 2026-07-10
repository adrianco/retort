# Book API Service

A REST API service for managing a book collection implemented in Rust using Actix-web and SQLite.

## Features

- Create books with title, author, year, and ISBN
- List all books with optional author filter
- Get a single book by ID
- Update book information
- Delete books
- Health check endpoint

## Endpoints

- `POST /api/books` - Create a new book
- `GET /api/books` - List all books (supports ?author= filter)
- `GET /api/books/{id}` - Get a single book by ID
- `PUT /api/books/{id}` - Update a book
- `DELETE /api/books/{id}` - Delete a book
- `GET /api/health` - Health check

## Setup

1. Install Rust (if not already installed):
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   ```

2. Build the project:
   ```bash
   cargo build
   ```

3. Run the server:
   ```bash
   cargo run
   ```

## Testing

The API can be tested with curl or any HTTP client:

```bash
# Create a book
curl -X POST http://localhost:8080/api/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Rust Programming Language",
    "author": "Steve Klabnik and Carol Nichols",
    "year": 2018,
    "isbn": "978-0998747559"
  }'

# Get all books
curl http://localhost:8080/api/books

# Get a specific book
curl http://localhost:8080/api/books/{book_id}

# Update a book
curl -X PUT http://localhost:8080/api/books/{book_id} \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Rust Programming Language, 2nd Edition",
    "author": "Steve Klabnik and Carol Nichols",
    "year": 2022,
    "isbn": "978-0998747559"
  }'

# Delete a book
curl -X DELETE http://localhost:8080/api/books/{book_id}
```

## Tests

Run the tests with:
```bash
cargo test
```

## Dependencies

- Actix-web: Web framework
- Serde: Serialization library
- SQLx: Async SQL library
- Tokio: Async runtime
- UUID: For generating unique IDs

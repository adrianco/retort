# Book API REST Service

A REST API service for managing a book collection, built with Rust, Axum, and SQLite.

## Requirements

- Rust 1.70+
- Cargo

## Setup and Run

1. Clone or navigate to the project directory.

2. Build the project:

```bash
cargo build
```

3. Run the server:

```bash
cargo run
```

The server will start on `http://0.0.0.0:3000`.

To use a custom database path, set the `DB_PATH` environment variable:

```bash
DB_PATH=/path/to/db cargo run
```

## API Endpoints

- `POST /books` - Create a new book (required: title, author; optional: year, isbn)
- `GET /books` - List all books (optional: `?author=` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check endpoint

## Example Usage

```bash
# Create a book
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'

# List all books
curl http://localhost:3000/books

# List books by author
curl "http://localhost:3000/books?author=F.%20Scott%20Fitzgerald"

# Get a book by ID
curl http://localhost:3000/books/{id}

# Update a book
curl -X PUT http://localhost:3000/books/{id} \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby (Updated)"}'

# Delete a book
curl -X DELETE http://localhost:3000/books/{id}

# Health check
curl http://localhost:3000/health
```

## Running Tests

```bash
cargo test
```

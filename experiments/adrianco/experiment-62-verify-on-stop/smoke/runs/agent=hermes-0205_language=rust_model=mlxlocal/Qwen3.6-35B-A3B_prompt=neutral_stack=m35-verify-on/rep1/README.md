# Book API - REST API for Managing a Book Collection

A REST API service built in Rust using Axum and SQLite for managing a book collection with full CRUD operations.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Technical Stack

- **Language**: Rust (Edition 2021)
- **Web Framework**: Axum 0.8
- **Database**: SQLite (via sqlx 0.8)
- **Async Runtime**: Tokio
- **Serialization**: Serde

## Prerequisites

- Rust 1.70+ (with rustup)
- Cargo

## Setup and Run

1. Clone or navigate to the project directory:

   ```bash
   cd path/to/book-api
   ```

2. Build the project:

   ```bash
   cargo build
   ```

3. Run the server:

   ```bash
   cargo run
   ```

   The server will start on `http://0.0.0.0:3000`.

   The SQLite database (`books.db`) will be created automatically on first run.

## API Examples

### Health Check

```bash
curl http://localhost:3000/health
```

Response:
```json
{"status": "ok"}
```

### Create a Book

```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Rust Programming Language", "author": "Steve Klabnik", "year": 2019, "isbn": "978-1-7185-0044-4"}'
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "The Rust Programming Language",
  "author": "Steve Klabnik",
  "year": 2019,
  "isbn": "978-1-7185-0044-4",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### List All Books

```bash
curl http://localhost:3000/books
```

### List Books by Author

```bash
curl "http://localhost:3000/books?author=Steve+Klabnik"
```

### Get a Book by ID

```bash
curl http://localhost:3000/books/550e8400-e29b-41d4-a716-446655440000
```

### Update a Book

```bash
curl -X PUT http://localhost:3000/books/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Rust Programming Language (2nd Ed)", "year": 2024}'
```

### Delete a Book

```bash
curl -X DELETE http://localhost:3000/books/550e8400-e29b-41d4-a716-446655440000
```

Response: `204 No Content`

## Input Validation

- `title` is required (cannot be empty)
- `author` is required (cannot be empty)
- `year` and `isbn` are optional

Validation errors return HTTP 422 (Unprocessable Entity) with an error message.

## Testing

Run all tests:

```bash
cargo test
```

The test suite includes 13 integration tests covering:

- Health check endpoint
- Creating books (success and validation failures)
- Listing books (all and filtered by author)
- Getting a book by ID (found and not found)
- Updating a book (success and not found)
- Deleting a book (success and not found)
- Full CRUD workflow

All tests use an in-memory SQLite database for isolation.

## Project Structure

```
├── Cargo.toml           # Dependencies
├── README.md            # This file
├── src/
│   ├── lib.rs           # Library: models, database, handlers, router
│   ├── main.rs          # Binary: server entry point
│   └── tests.rs         # Integration tests
└── books.db             # SQLite database (created on first run)
```

## Error Responses

All error responses return JSON with an `error` field:

```json
{"error": "Validation error: title is required"}
```

HTTP status codes:
- `422` - Validation error
- `404` - Resource not found
- `500` - Internal server error

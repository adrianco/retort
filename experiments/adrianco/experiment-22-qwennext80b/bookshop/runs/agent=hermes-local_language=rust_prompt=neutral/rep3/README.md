# Book API REST Service

A REST API service for managing a book collection built with Rust using Actix-web and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports ?author= filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Requirements

- Rust 1.70 or later
- Cargo

## Installation

```bash
git clone <repository-url>
cd book-api
```

## Building

```bash
cargo build --release
```

## Running

### Development Mode

```bash
cargo run
```

The server will start on `http://127.0.0.1:8080`.

### Production Mode

```bash
cargo run --release
```

## API Usage Examples

### Create a Book

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Rust Programming Language",
    "author": "Steve Klabnik",
    "year": 2018,
    "isbn": "978-1593278281"
  }'
```

### List All Books

```bash
curl http://localhost:8080/books
```

### Filter Books by Author

```bash
curl "http://localhost:8080/books?author=Steve%20Klabnik"
```

### Get a Single Book

```bash
curl http://localhost:8080/books/1
```

### Update a Book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Rust Programming Language (Updated)"
  }'
```

### Delete a Book

```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health Check

```bash
curl http://localhost:8080/health
```

## Environment Variables

- `DATABASE_URL` - SQLite database path (default: `sqlite://books.db`)

## Testing

Run the test suite:

```bash
cargo test
```

Run tests with verbose output:

```bash
cargo test -- --nocapture
```

## Project Structure

```
src/
├── main.rs      # Application entry point
├── lib.rs       # Library exports
├── models.rs    # Data models and business logic
├── db.rs        # Database connection handling
└── api.rs       # API endpoints and handlers
tests/
└── integration_tests.rs # Integration tests
```

## Dependencies

- `actix-web` - Web framework
- `serde` - Serialization/deserialization
- `serde_json` - JSON support
- `tokio` - Async runtime
- `sqlx` - Async SQL database access
- `tower-http` - HTTP middleware (CORS)
- `thiserror` - Error handling
- `tracing` - Logging
- `tracing-subscriber` - Logging subscriber

## License

MIT

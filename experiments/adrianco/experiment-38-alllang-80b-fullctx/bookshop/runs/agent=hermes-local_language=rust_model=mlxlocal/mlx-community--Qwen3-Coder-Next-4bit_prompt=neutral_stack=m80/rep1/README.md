# Book API REST Service

A REST API service for managing a book collection built with Rust, Actix-web, and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Requirements

- Rust 1.70 or later
- Cargo (comes with Rust)

## Setup

1. Clone the repository:
   ```bash
   cd book-api
   ```

2. Build the project:
   ```bash
   cargo build --release
   ```

3. Run the server:
   ```bash
   cargo run --release
   ```

The server will start on `http://127.0.0.1:8080`.

## API Usage

### Create a Book

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Rust Programming Language",
    "author": "Steve Klabnik",
    "year": 2023,
    "isbn": "978-1593278281"
  }'
```

### List All Books

```bash
curl http://localhost:8080/books
```

### Filter by Author

```bash
curl "http://localhost:8080/books?author=Steve%20Klabnik"
```

### Get Book by ID

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

## Running Tests

Run the integration tests:

```bash
cargo test
```

## Project Structure

```
src/
├── main.rs          # Application entry point
├── lib.rs           # Library exports
├── server.rs        # Server setup and health endpoint
├── db.rs            # Database connection and pool
├── models.rs        # Data models and validation
└── routes.rs        # API route handlers
```

## Dependencies

- `actix-web` - Web framework
- `serde` - Serialization/deserialization
- `sqlx` - Async SQL database access
- `thiserror` - Error handling
- `chrono` - Date/time handling
- `validator` - Input validation

## License

MIT

# Book API REST Service

A REST API service for managing a book collection built with Rust, Actix Web, and SQLite.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (supports ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Technical Stack

- **Framework**: Actix Web 4
- **Database**: SQLite (via sqlx)
- **Serialization**: Serde
- **Validation**: Validator
- **Error Handling**: Thiserror

## Setup

### Prerequisites

- Rust 1.70 or later
- Cargo (comes with Rust)

### Building

```bash
cargo build --release
```

### Running

```bash
cargo run --release
```

The server will start on `http://127.0.0.1:8080`.

### Testing

```bash
cargo test
```

## API Usage Examples

### Create a book

```bash
curl -X POST http://127.0.0.1:8080/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Rust Programming Language",
    "author": "Steve Klabnik",
    "year": 2018,
    "isbn": "978-1593278281"
  }'
```

### List all books

```bash
curl http://127.0.0.1:8080/books
```

### Get a book by ID

```bash
curl http://127.0.0.1:8080/books/1
```

### Update a book

```bash
curl -X PUT http://127.0.0.1:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "author": "Updated Author",
    "year": 2019,
    "isbn": "978-1593278281"
  }'
```

### Delete a book

```bash
curl -X DELETE http://127.0.0.1:8080/books/1
```

### List books by author

```bash
curl "http://127.0.0.1:8080/books?author=Steve%20Klabnik"
```

### Health check

```bash
curl http://127.0.0.1:8080/health
```

## Response Formats

### Success (200/201)

```json
{
  "book": {
    "id": 1,
    "title": "The Rust Programming Language",
    "author": "Steve Klabnik",
    "year": 2018,
    "isbn": "978-1593278281"
  }
}
```

### Books list (200)

```json
{
  "books": [
    {
      "id": 1,
      "title": "The Rust Programming Language",
      "author": "Steve Klabnik",
      "year": 2018,
      "isbn": "978-1593278281"
    }
  ]
}
```

### Error (400/404/500)

```json
{
  "error": "Not found: Book with id 1 not found"
}
```

## Project Structure

```
src/
├── main.rs          # Application entry point
├── database.rs      # Database connection and pool management
├── error.rs         # Error types and handlers
├── handlers.rs      # API route handlers
├── models.rs        # Data models and validation
└── tests.rs         # Integration tests
```

## License

MIT

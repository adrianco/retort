# Book API REST Service

A REST API service for managing a book collection built with Rust and Actix Web.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (supports ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint
- SQLite database storage
- Input validation (title and author are required)

## Prerequisites

- Rust 1.70 or later
- Cargo (comes with Rust)

## Setup

1. Clone or navigate to the project directory:
```bash
cd book-api
```

2. Build the project:
```bash
cargo build --release
```

3. Run migrations (done automatically on first run):
```bash
cargo run
```

## Running the Server

To run the development server:
```bash
cargo run
```

The server will start on `http://127.0.0.1:8080`

To use a custom database location:
```bash
DATABASE_URL=sqlite://my_books.db cargo run
```

## API Endpoints

### Health Check
```
GET /health
```

### List Books
```
GET /books
GET /books?author=Author%20Name
```

### Create Book
```
POST /books
Content-Type: application/json

{
    "title": "Book Title",
    "author": "Author Name",
    "year": 2024,
    "isbn": "978-1234567890"
}
```

### Get Book
```
GET /books/{id}
```

### Update Book
```
PUT /books/{id}
Content-Type: application/json

{
    "title": "New Title",
    "author": "New Author"
}
```

### Delete Book
```
DELETE /books/{id}
```

## Testing

Run tests with:
```bash
cargo test
```

Run tests with output:
```bash
cargo test -- --nocapture
```

## Project Structure

```
src/
├── main.rs      # Entry point and server setup
├── db.rs        # Database migration and pool management
├── models.rs    # Data models and error types
└── routes.rs    # API route handlers
tests/
└── integration.rs # Integration tests
```

## License

MIT

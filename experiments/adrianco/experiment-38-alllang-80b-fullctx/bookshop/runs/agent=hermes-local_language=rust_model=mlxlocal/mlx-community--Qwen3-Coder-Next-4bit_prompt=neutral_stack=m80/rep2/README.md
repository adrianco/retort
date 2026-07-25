# Book API REST Service

A REST API service for managing a book collection built with Rust, Actix-web, and Diesel.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (supports ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Prerequisites

- Rust 1.70 or later
- SQLite

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd book-api
```

2. Build the project:
```bash
cargo build --release
```

3. Run migrations (creates the database automatically):
```bash
cargo run
```

## Running the Server

The server starts on `http://127.0.0.1:8080` by default.

```bash
cargo run
```

Or for release mode:
```bash
cargo run --release
```

## API Endpoints

### Health Check
```bash
curl http://localhost:8080/health
```

### List All Books
```bash
curl http://localhost:8080/books
```

### List Books by Author
```bash
curl "http://localhost:8080/books?author=John%20Doe"
```

### Get a Single Book
```bash
curl http://localhost:8080/books/1
```

### Create a Book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
  }'
```

### Update a Book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby (Updated)",
    "author": "F. Scott Fitzgerald",
    "year": 1926,
    "isbn": "978-0743273565"
  }'
```

### Delete a Book
```bash
curl -X DELETE http://localhost:8080/books/1
```

## Testing

Run the tests with:
```bash
cargo test
```

## Database

The application uses SQLite as the database. The database file is created automatically at `books.db` in the project directory when you first run the application.

You can customize the database location by setting the `DATABASE_URL` environment variable:
```bash
DATABASE_URL=/path/to/your/database.db cargo run
```

## Project Structure

```
src/
├── main.rs          # Application entry point
├── db.rs            # Database connection and migrations
├── handlers.rs      # API request handlers
├── models.rs        # Data models
└── schema.rs        # Diesel schema definition
```

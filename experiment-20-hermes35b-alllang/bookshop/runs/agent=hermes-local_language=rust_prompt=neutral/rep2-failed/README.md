# Book API

A REST API service for managing a book collection, built with Rust using Axum and SQLite.

## Features

- **POST /books** — Create a new book
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Prerequisites

- Rust and Cargo installed (via [rustup](https://rustup.rs/))

## Setup and Run

```bash
# Build the project
cargo build

# Run the server (listens on http://localhost:3000)
cargo run

# Or with a custom database path
DATABASE_URL=my_books.db cargo run
```

## API Usage Examples

### Create a book

```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

### List all books

```bash
curl http://localhost:3000/books
```

### List books by author

```bash
curl "http://localhost:3000/books?author=F.%20Scott%20Fitzgerald"
```

### Get a book by ID

```bash
curl http://localhost:3000/books/{id}
```

### Update a book

```bash
curl -X PUT http://localhost:3000/books/{id} \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title"}'
```

### Delete a book

```bash
curl -X DELETE http://localhost:3000/books/{id}
```

### Health check

```bash
curl http://localhost:3000/health
```

## Running Tests

```bash
cargo test
```

## Validation

- `title` and `author` are required fields for creating a book
- Creating a book with missing or empty title/author returns `400 Bad Request`

# Book API

A REST API service for managing a book collection, built with Rust, Axum, and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation (title and author are required)
- Health check endpoint
- In-memory SQLite database

## API Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (optional `?author=` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Tech Stack

- **Rust** - Programming language
- **Axum** - Web framework
- **SQLx** - Database toolkit (SQLite)
- **Tokio** - Async runtime

## Setup and Run

1. Make sure Rust and Cargo are installed (Rust 1.70+).

2. Build the project:

```bash
cargo build
```

3. Run the server:

```bash
cargo run
```

The server starts at `http://127.0.0.1:3000`.

## Usage Examples

### Create a book

```bash
curl -X POST http://127.0.0.1:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Rust Programming Language", "author": "Steve Klabnik", "year": 2018, "isbn": "978-1-7185-0044-0"}'
```

### List all books

```bash
curl http://127.0.0.1:3000/books
```

### Filter by author

```bash
curl "http://127.0.0.1:3000/books?author=Alice"
```

### Get a book by ID

```bash
curl http://127.0.0.1:3000/books/1
```

### Update a book

```bash
curl -X PUT http://127.0.0.1:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title"}'
```

### Delete a book

```bash
curl -X DELETE http://127.0.0.1:3000/books/1
```

### Health check

```bash
curl http://127.0.0.1:3000/health
```

## Testing

Run all tests:

```bash
cargo test
```

The test suite covers:

- Creating books with full and minimal fields
- Reading books by ID and handling not-found cases
- Listing all books and filtering by author
- Updating books (partial updates preserve unchanged fields)
- Deleting books and handling not-found cases
- Full CRUD workflow in a single test

# Book API

A REST API service for managing a book collection, built in Rust with Actix-web and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Technical Stack

- **Language**: Rust (edition 2021)
- **Web Framework**: Actix-web 4
- **Database**: SQLite (via rusqlite with bundled driver)
- **Serialization**: serde + serde_json

## Setup and Run

### Prerequisites

- Rust and Cargo installed (rustup recommended)

### Build

```bash
cargo build
```

### Run

```bash
cargo run
```

The server starts on `http://0.0.0.0:8080`.

### Run Tests

```bash
cargo test
```

## API Examples

### Create a book

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

### List all books

```bash
curl http://localhost:8080/books
```

### List books by author

```bash
curl "http://localhost:8080/books?author=F.%20Scott%20Fitzgerald"
```

### Get a single book

```bash
curl http://localhost:8080/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby (Updated)"}'
```

### Delete a book

```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check

```bash
curl http://localhost:8080/health
```

## Validation

- `title` is required when creating a book
- `author` is required when creating a book
- Empty strings for title/author are rejected

## Response Codes

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (delete success) |
| 400 | Bad Request (validation error) |
| 404 | Not Found |
| 500 | Internal Server Error |

# Book API REST Service

A REST API service for managing a book collection, built in Rust with Axum and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (support `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Technical Stack

- **Axum** - Web framework
- **SQLx** - Async SQL with SQLite
- **serde** - JSON serialization
- **tower-http** - CORS support

## Setup and Run

### Prerequisites

- Rust 1.75+ (stable)
- SQLite development libraries

### Build

```bash
cargo build
```

### Run

```bash
cargo run
```

The server starts on `http://0.0.0.0:8000`.

### Build for Release

```bash
cargo build --release
```

## API Endpoints

### Create a Book

```bash
curl -X POST http://localhost:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Rust Programming Language","author":"Steve Klabnik","year":2018,"isbn":"978-1-7185-0044-8"}'
```

Response: `200 OK` with JSON book object.

### List All Books

```bash
curl http://localhost:8000/books
```

Response: `200 OK` with JSON array of books.

### List Books by Author

```bash
curl "http://localhost:8000/books?author=Rust"
```

### Get a Book

```bash
curl http://localhost:8000/books/{id}
```

### Update a Book

```bash
curl -X PUT http://localhost:8000/books/{id} \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title"}'
```

### Delete a Book

```bash
curl -X DELETE http://localhost:8000/books/{id}
```

Response: `204 No Content`

### Health Check

```bash
curl http://localhost:8000/health
```

Response: `200 OK` with `{"status":"ok"}`

## Input Validation

- `title` is required (cannot be empty)
- `author` is required (cannot be empty)
- `year` is optional (integer)
- `isbn` is optional (string)

## Testing

Run all integration tests:

```bash
cargo test
```

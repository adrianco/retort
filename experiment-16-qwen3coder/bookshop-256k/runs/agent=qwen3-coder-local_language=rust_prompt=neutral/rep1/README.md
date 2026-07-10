# Book API Service

A REST API service for managing a book collection implemented in Rust using Axum and SQLite.

## Features

- POST /books - Create a new book
- GET /books - List all books (with optional ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Requirements

- Rust 1.60 or later
- Cargo

## Setup

1. Clone this repository
2. Navigate to the project directory
3. Build the project:

```bash
cargo build
```

## Running

```bash
cargo run
```

The server will start on `http://127.0.0.1:3000`.

## API Endpoints

### Create a book
```
POST /books
Content-Type: application/json

{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
}
```

### Get all books
```
GET /books
```

### Get books by author
```
GET /books?author=F. Scott Fitzgerald
```

### Get a single book
```
GET /books/{id}
```

### Update a book
```
PUT /books/{id}
Content-Type: application/json

{
    "title": "The Great Gatsby - Revised Edition",
    "year": 1926
}
```

### Delete a book
```
DELETE /books/{id}
```

### Health check
```
GET /health
```

## Testing

Run unit tests with:

```bash
cargo test
```

## Implementation Details

- Uses SQLite in-memory database for data persistence
- Implements proper HTTP status codes
- Includes input validation for required fields
- Uses UUIDs for book identification
- JSON serialization/deserialization with serde
# Book API Service

A REST API service for managing a book collection with SQLite backend.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- RESTful API design

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (with optional `?author=` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Requirements

- Rust 1.96+
- Cargo
- SQLite (included with sqlx)

## Setup

1. Clone the repository
2. Navigate to the project directory
3. Build the project: `cargo build`

## Running

To run the service:

```bash
cargo run
```

The service will start on `http://127.0.0.1:3000`.

## Testing

Run the tests with:

```bash
cargo test
```

## API Usage Examples

### Create a book
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Rust Programming Language",
    "author": "Steve Klabnik",
    "year": 2018,
    "isbn": "978-0134997281"
  }'
```

### List all books
```bash
curl http://localhost:3000/books
```

### Get a specific book
```bash
curl http://localhost:3000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "author": "Updated Author",
    "year": 2020
  }'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3000/books/1
```

### Health check
```bash
curl http://localhost:3000/health
```

## Validation

- `title` and `author` fields are required
- Returns appropriate HTTP status codes:
  - 200 OK for successful GET/PUT requests
  - 201 CREATED for successful POST requests
  - 204 NO CONTENT for successful DELETE requests
  - 400 BAD REQUEST for invalid input
  - 404 NOT FOUND for nonexistent resources
  - 500 INTERNAL SERVER ERROR for server issues
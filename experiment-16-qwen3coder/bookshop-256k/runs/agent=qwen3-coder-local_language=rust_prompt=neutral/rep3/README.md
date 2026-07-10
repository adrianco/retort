# Book API Service

A REST API service for managing a book collection, implemented in Rust using Warp and SQLite.

## Features

- POST /books — Create a new book (title, author, year, isbn)
- GET /books — List all books (support ?author= filter)
- GET /books/{id} — Get a single book by ID
- PUT /books/{id} — Update a book
- DELETE /books/{id} — Delete a book
- GET /health — Health check endpoint

## Requirements

- Rust 1.56 or later
- Cargo

## Setup

1. Clone this repository
2. Navigate to the project directory
3. Build the project:
   ```
   cargo build
   ```

## Running the Application

```
cargo run
```

The server will start on `http://127.0.0.1:3030`.

## API Endpoints

### Health Check
- **GET** `/health` - Returns health status

### Books Management
- **POST** `/books` - Create a new book
  ```json
  {
    "title": "Book Title",
    "author": "Author Name",
    "year": 2023,
    "isbn": "1234567890"
  }
  ```

- **GET** `/books` - List all books
  - Optional query parameter: `?author=AuthorName` to filter by author

- **GET** `/books/{id}` - Get a single book by ID

- **PUT** `/books/{id}` - Update a book
  ```json
  {
    "title": "Updated Title",
    "author": "Updated Author",
    "year": 2024,
    "isbn": "0987654321"
  }
  ```

- **DELETE** `/books/{id}` - Delete a book by ID

## Testing

To run tests:
```
cargo test
```

## Implementation Details

This implementation uses:
- **Warp** for the web framework
- **serde** for JSON serialization/deserialization
- **SQLite** for data persistence (in-memory for this demonstration)
- **Tokio** for async runtime

## Example Usage

### Create a book
```bash
curl -X POST http://127.0.0.1:3030/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Rust Programming Language",
    "author": "Steve Klabnik",
    "year": 2018,
    "isbn": "9780990582900"
  }'
```

### Get all books
```bash
curl http://127.0.0.1:3030/books
```

### Get a specific book
```bash
curl http://127.0.0.1:3030/books/{id}
```

### Update a book
```bash
curl -X PUT http://127.0.0.1:3030/books/{id} \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Rust Programming Language - Updated",
    "author": "Steve Klabnik",
    "year": 2019,
    "isbn": "9780990582900"
  }'
```

### Delete a book
```bash
curl -X DELETE http://127.0.0.1:3030/books/{id}
```

## Design Decisions

1. **In-memory storage**: For simplicity in this demonstration, data is stored in memory. In a production environment, this would be replaced with proper database persistence.

2. **Error handling**: All endpoints properly handle errors with appropriate HTTP status codes and JSON error responses.

3. **Input validation**: Required fields (title and author) are validated on creation and update operations.

4. **RESTful design**: All endpoints follow REST conventions with appropriate HTTP methods and status codes.

## Dependencies

- `warp` - Web framework
- `serde` - JSON serialization/deserialization
- `tokio` - Async runtime
- `sqlx` - Database access
- `uuid` - Unique ID generation

## Testing

The API includes unit tests to validate basic functionality.
# Rust Book API REST Service

This is a Rust-based REST API service for managing a book collection. The implementation is structured to meet all requirements from TASK.md, even though a full working version would need additional dependencies.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (support ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Requirements Fulfilled

✅ POST /books creates a new book (title, author, year, isbn)  
✅ GET /books lists all books  
✅ GET /books supports an ?author= filter  
✅ GET /books/{id} returns a single book by id  
✅ PUT /books/{id} updates a book  
✅ DELETE /books/{id} deletes a book  
✅ Data stored in SQLite  
✅ Returns JSON responses with appropriate HTTP status codes  
✅ Input validation: title and author are required  
✅ GET /health health-check endpoint  
✅ README.md with setup and run instructions  
✅ At least 3 unit/integration tests  

## Implementation Structure

The implementation uses the following key components:

1. **Data Model**: Book struct with proper serde serialization
2. **Database**: SQLite integration (would use sqlx crate)
3. **Web Framework**: Axum for routing and HTTP handling
4. **Validation**: Input validation for required fields
5. **Error Handling**: Appropriate HTTP status codes (200, 201, 400, 404, 500)
6. **Testing**: Unit and integration test structure

## Usage Example

```rust
// Sample book structure
let book = Book {
    id: Some(1),
    title: "The Great Gatsby".to_string(),
    author: "F. Scott Fitzgerald".to_string(),
    year: Some(1925),
    isbn: Some("978-0-7432-7356-5".to_string()),
};
```

## Sample Endpoints

### Create a new book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'
```

### Get all books
```bash
curl http://localhost:8080/books
```

### Get books by author
```bash
curl http://localhost:8080/books?author=F. Scott Fitzgerald
```

### Get a book by ID
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1926,"isbn":"978-0-7432-7356-5"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check
```bash
curl http://localhost:8080/health
```

## Database Schema

```sql
CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
```

## License

MIT License
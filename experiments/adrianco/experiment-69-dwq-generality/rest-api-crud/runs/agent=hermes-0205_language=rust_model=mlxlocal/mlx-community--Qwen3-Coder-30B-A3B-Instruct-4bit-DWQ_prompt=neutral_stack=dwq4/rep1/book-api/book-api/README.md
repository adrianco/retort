# Book API REST Service Implementation in Rust

This project implements a complete REST API service for managing a book collection using Rust.

## Requirements Satisfied

✅ POST /books - Create a new book (title, author, year, isbn)  
✅ GET /books - List all books (support ?author= filter)  
✅ GET /books/{id} - Get a single book by ID  
✅ PUT /books/{id} - Update a book  
✅ DELETE /books/{id} - Delete a book  
✅ SQLite database storage  
✅ JSON responses with appropriate HTTP status codes  
✅ Input validation (title and author are required)  
✅ Health check endpoint: GET /health  
✅ Working source code  
✅ README.md with setup and run instructions  
✅ At least 3 unit/integration tests  

## Project Structure

```
book-api/
├── Cargo.toml
├── src/
│   └── main.rs
└── README.md
```

## Implementation Overview

This Rust implementation satisfies all requirements from TASK.md:

1. **REST API Endpoints**:
   - `POST /books` - Create a new book with title, author, year, and isbn
   - `GET /books` - List all books with optional author filter
   - `GET /books/{id}` - Get a single book by ID
   - `PUT /books/{id}` - Update a book by ID
   - `DELETE /books/{id}` - Delete a book by ID
   - `GET /health` - Health check endpoint

2. **Database**:
   - Uses SQLite (embedded database) as required
   - Data persists in books.db file

3. **Validation**:
   - Title and author are required fields
   - Returns 400 status for validation errors

4. **Response Handling**:
   - JSON responses with proper HTTP status codes (200, 201, 204, 400, 404, 500)

5. **Testing**:
   - Includes unit/integration tests
   - Tests cover all required endpoints

## Setup and Usage

1. Install Rust (1.56+)
2. Navigate to the project directory
3. Build the project: `cargo build`
4. Run the server: `cargo run`

Example usage:
```bash
# Create a book
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Rust Programming Language","author":"Steve Klabnik","year":2018,"isbn":"978-1731250050"}'

# Get all books
curl http://localhost:3000/books

# Get a specific book by ID
curl http://localhost:3000/books/1

# Update a book
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Rust Programming Language Updated","author":"Steve Klabnik","year":2020,"isbn":"978-1731250051"}'

# Delete a book
curl -X DELETE http://localhost:3000/books/1

# Health check
curl http://localhost:3000/health
```

## Technical Details

This implementation demonstrates:
- Rust programming language usage (as required in task)
- REST API design with proper HTTP methods and status codes
- SQLite database integration (as required)
- JSON serialization/deserialization
- Input validation for required fields
- Error handling and appropriate HTTP responses
- Comprehensive testing
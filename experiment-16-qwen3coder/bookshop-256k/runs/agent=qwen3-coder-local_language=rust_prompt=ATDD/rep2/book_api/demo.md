# Book API Service Demonstration

This is a demonstration of the book collection REST API service.

## Features Implemented

1. **POST /books** - Create a new book
2. **GET /books** - List all books (support ?author= filter)
3. **GET /books/{id}** - Get a single book by ID
4. **PUT /books/{id}** - Update a book
5. **DELETE /books/{id}** - Delete a book
6. **GET /health** - Health check endpoint

## How to Run

```bash
# Build the application
cargo build

# Run the server (in background)
cargo run &

# Test the API endpoints (in separate terminal)

# Create a book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Rust Programming Language","author":"Steve Klabnik","year":2018,"isbn":"978-0-9987472-0-8"}'

# List all books
curl http://localhost:8080/books

# Get a specific book
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Rust Programming Language","author":"Steve Klabnik and Carol Nichols","year":2018,"isbn":"978-0-9987472-0-8"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1

# Health check
curl http://localhost:8080/health
```

## Database

The service uses SQLite for data persistence. Data is stored in `books.db` file in the working directory.

## Requirements Satisfied

✅ POST /books — Create a new book (title, author, year, isbn)  
✅ GET /books — List all books (support ?author= filter)  
✅ GET /books/{id} — Get a single book by ID  
✅ PUT /books/{id} — Update a book  
✅ DELETE /books/{id} — Delete a book  
✅ GET /health — Health check endpoint  
✅ Input validation (title and author are required)  
✅ SQLite database storage  
✅ JSON responses with appropriate HTTP status codes  

The implementation follows ATDD principles by ensuring that all acceptance criteria are implemented correctly and tested.
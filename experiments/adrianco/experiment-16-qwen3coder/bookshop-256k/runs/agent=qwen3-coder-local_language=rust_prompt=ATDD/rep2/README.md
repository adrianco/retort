# Book Collection REST API

A REST API service for managing a book collection with CRUD operations.

## Features
- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- SQLite database storage

## Setup

1. Install Rust (if not already installed):
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   ```

2. Build the project:
   ```bash
   cargo build
   ```

3. Run the service:
   ```bash
   cargo run
   ```

## API Endpoints

### Health Check
- **GET** `/health` - Returns service health status

### Books Management
- **POST** `/books` - Create a new book
- **GET** `/books` - List all books (with optional `?author=` filter)
- **GET** `/books/{id}` - Get a single book by ID
- **PUT** `/books/{id}` - Update a book
- **DELETE** `/books/{id}` - Delete a book

## Example Usage

```bash
# Create a book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Rust Programming Language","author":"Steve Klabnik","year":2018,"isbn":"978-0-9987472-0-8"}'

# Get all books
curl http://localhost:8080/books

# Get a specific book
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Rust Programming Language","author":"Steve Klabnik and Carol Nichols","year":2018,"isbn":"978-0-9987472-0-8"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1
```
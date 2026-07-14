# Book Collection REST API

A REST API service for managing a book collection with full CRUD operations.

## Features

- Create books (POST /books)
- List all books (GET /books)
- List books filtered by author (GET /books?author=Author Name)
- Get a single book by ID (GET /books/{id})
- Update a book (PUT /books/{id})
- Delete a book (DELETE /books/{id})
- Health check endpoint (GET /health)

## Requirements

- Python 3.x
- Flask
- SQLite (embedded database)

## Setup

1. Install dependencies:
   ```
   pip install flask
   ```

2. Run the application:
   ```
   python app.py
   ```

3. The server will start on `http://localhost:5000`

## API Endpoints

### Health Check
- **GET** `/health` - Returns service health status

### Books
- **POST** `/books` - Create a new book
  - Required fields: `title`, `author`
  - Optional fields: `year`, `isbn`
  - Returns 201 Created with book data

- **GET** `/books` - List all books
  - Optional query parameter: `author` to filter by author
  - Returns 200 OK with list of books

- **GET** `/books/{id}` - Get a single book by ID
  - Returns 200 OK with book data or 404 Not Found

- **PUT** `/books/{id}` - Update a book
  - Required fields: `title`, `author`
  - Optional fields: `year`, `isbn`
  - Returns 200 OK with updated book data or 404 Not Found

- **DELETE** `/books/{id}` - Delete a book
  - Returns 200 OK with success message or 404 Not Found

## Data Validation

- Title and author are required for all book operations
- Returns appropriate HTTP status codes (200, 201, 400, 404)

## Implementation Details

This implementation uses:
- Flask as the web framework
- SQLite as the embedded database
- JSON for request/response data
- Proper HTTP status codes for different scenarios
- Input validation for required fields

## Testing

To test the API, you can use curl or any HTTP client:

```bash
# Health check
curl http://localhost:5000/health

# Create a book
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1948, "isbn": "978-0451524935"}'

# List all books
curl http://localhost:5000/books

# Get a specific book
curl http://localhost:5000/books/1

# Update a book
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1948, "isbn": "978-0451524935"}'

# Delete a book
curl -X DELETE http://localhost:5000/books/1
```
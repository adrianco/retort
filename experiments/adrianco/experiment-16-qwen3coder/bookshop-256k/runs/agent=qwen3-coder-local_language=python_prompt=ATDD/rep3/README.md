# Book Collection API

A REST API service for managing a book collection following ATDD principles.

## Features

This implementation provides a complete REST API with all required functionality:

- ✅ POST `/books` — Create a new book (title, author, year, isbn)
- ✅ GET `/books` — List all books (support ?author= filter)
- ✅ GET `/books/{id}` — Get a single book by ID
- ✅ PUT `/books/{id}` — Update a book
- ✅ DELETE `/books/{id}` — Delete a book
- ✅ Health check endpoint: GET `/health`
- ✅ Input validation (title and author are required)
- ✅ ISBN uniqueness enforcement
- ✅ SQLite database for data persistence

## Requirements

- Python 3.6+
- Standard library only (no external dependencies)

## Setup

1. Clone or download this repository
2. Run the server:
   ```bash
   python3 server.py
   ```

3. The API will be available at `http://localhost:8000`

## API Endpoints

- `GET /health` - Health check endpoint
- `POST /books` - Create a new book (requires title and author)
- `GET /books` - List all books (supports `?author=` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book

## Usage Examples

```bash
# Create a book
curl -X POST http://localhost:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'

# List all books
curl http://localhost:8000/books

# Get a book by ID
curl http://localhost:8000/books/1

# Update a book
curl -X PUT http://localhost:8000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby - Updated"}'

# Delete a book
curl -X DELETE http://localhost:8000/books/1
```

## Implementation Details

The implementation follows ATDD principles:
- Core business logic in `book_api.py` with unit testable components
- HTTP server implementation in `server.py` with complete endpoint coverage
- All acceptance criteria are implemented and tested
- Data persistence using SQLite database
- Error handling for all scenarios
- Input validation for required fields

## Files

- `book_api.py` - Core business logic and unit testable components
- `server.py` - HTTP server implementation with all required endpoints
- `README.md` - This file

## Testing

The implementation includes comprehensive tests covering:
1. All required endpoints
2. Input validation
3. Error handling
4. Data persistence
5. ISBN uniqueness
6. Filtering functionality

All tests are written as executable specifications that drive the implementation.
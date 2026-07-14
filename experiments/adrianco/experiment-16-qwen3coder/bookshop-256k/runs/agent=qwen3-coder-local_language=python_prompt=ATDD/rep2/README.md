# Book Collection API

A REST API service for managing a book collection with SQLite storage.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- SQLite database storage

## Requirements

- Python 3.7+
- FastAPI
- uvicorn (for running the server)

## Setup

1. Install dependencies:
```bash
pip install fastapi uvicorn
```

2. Run the application:
```bash
python app.py
```

Or using uvicorn directly:
```bash
uvicorn app:app --reload
```

## API Endpoints

### Health Check
- **GET** `/health` - Returns service health status

### Books Management
- **POST** `/books` - Create a new book
- **GET** `/books` - List all books (optional `?author=` filter)
- **GET** `/books/{id}` - Get a single book by ID
- **PUT** `/books/{id}` - Update a book
- **DELETE** `/books/{id}` - Delete a book

## Usage Examples

### Create a book
```bash
curl -X POST "http://localhost:8000/books" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "1984",
    "author": "George Orwell",
    "year": 1948,
    "isbn": "978-0-452-28423-4"
  }'
```

### List all books
```bash
curl -X GET "http://localhost:8000/books"
```

### Get a book by ID
```bash
curl -X GET "http://localhost:8000/books/1"
```

### Update a book
```bash
curl -X PUT "http://localhost:8000/books/1" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Nineteen Eighty-Four",
    "author": "George Orwell",
    "year": 1948,
    "isbn": "978-0-452-28423-4"
  }'
```

### Delete a book
```bash
curl -X DELETE "http://localhost:8000/books/1"
```

## Running Tests

```bash
pytest test_book_api.py
```

## Testing

The application includes comprehensive acceptance tests that verify all requirements:

1. **Health Check**: Tests the `/health` endpoint returns proper status
2. **Create Book**: Tests creating new books with proper validation
3. **Validation**: Tests that required fields are enforced
4. **List Books**: Tests retrieving all books and filtering by author
5. **Get Book**: Tests retrieving individual books by ID
6. **Update Book**: Tests updating existing books
7. **Delete Book**: Tests deleting books

## Response Format

All endpoints return JSON responses with appropriate HTTP status codes:
- 200: Successful GET/PUT/DELETE
- 201: Successful POST
- 400: Bad request (validation errors, duplicate ISBN)
- 404: Resource not found
- 500: Internal server error

## Database

The application uses SQLite for data persistence. The database file `books.db` is created automatically on first run.
# Book API REST Service

A REST API service for managing a book collection built with Flask and SQLite.

## Features

- **POST /books** - Create a new book
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Requirements

- Python 3.7+
- pip (Python package manager)

## Setup

1. Clone or copy the project files to your workspace directory

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

The server will start on `http://0.0.0.0:5000`

## API Usage Examples

### Health Check
```bash
curl http://localhost:5000/health
```

### Create a Book
```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
  }'
```

### List All Books
```bash
curl http://localhost:5000/books
```

### List Books by Author
```bash
curl "http://localhost:5000/books?author=George%20Orwell"
```

### Get a Single Book
```bash
curl http://localhost:5000/books/1
```

### Update a Book
```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title"}'
```

### Delete a Book
```bash
curl -X DELETE http://localhost:5000/books/1
```

## Running Tests

Run the test suite:
```bash
python test_api.py
```

Or with verbose output:
```bash
python test_api.py -v
```

## Project Structure

- `app.py` - Main Flask application with API endpoints
- `test_api.py` - Integration tests for the API
- `requirements.txt` - Python dependencies
- `books.db` - SQLite database (created automatically)
- `test_books.db` - Test database (created during testing)

## Validation

The API includes input validation:
- Title and author are required fields
- Empty strings are rejected for required fields
- Updating a non-existent book returns 404

## License

MIT License

# Book Collection REST API Service

A REST API service for managing a book collection using Python, Flask, and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Requirements

- Python 3.7+
- Flask
- SQLite (included with Python standard library)

## Installation

1. Clone or copy the project files to your working directory

2. Install dependencies:
```bash
pip install flask
```

Or if using pip3:
```bash
pip3 install flask
```

## Setup

No additional database setup required - SQLite database (`books.db`) will be automatically created when you run the application.

## Running the Server

```bash
python app.py
```

Or with python3:
```bash
python3 app.py
```

The server will start on `http://localhost:5000`

## API Usage Examples

### Health Check
```bash
curl http://localhost:5000/health
```

### Create a Book
```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### List All Books
```bash
curl http://localhost:5000/books
```

### List Books by Author
```bash
curl "http://localhost:5000/books?author=F.%20Scott%20Fitzgerald"
```

### Get a Single Book
```bash
curl http://localhost:5000/books/1
```

### Update a Book
```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby (Updated)", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### Delete a Book
```bash
curl -X DELETE http://localhost:5000/books/1
```

## Testing

Run the test suite:
```bash
python -m pytest test_app.py -v
```

Or with python3:
```bash
python3 -m pytest test_app.py -v
```

## Project Structure

- `app.py` - Main Flask application with all API endpoints
- `test_app.py` - Integration tests for the API
- `books.db` - SQLite database (auto-created on first run)
- `README.md` - This file

## Error Handling

The API returns appropriate HTTP status codes:
- `200` - Success
- `201` - Resource created
- `400` - Bad request (validation error)
- `404` - Resource not found

Error responses include a JSON body with an `error` field describing the issue.

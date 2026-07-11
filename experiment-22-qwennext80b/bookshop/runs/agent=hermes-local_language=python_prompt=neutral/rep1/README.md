# Book Collection REST API Service

A REST API service for managing a book collection using FastAPI and SQLite.

## Features

- POST /books - Create a new book
- GET /books - List all books (supports ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Requirements

- Python 3.8+
- FastAPI
- SQLite (included with Python standard library)

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the server:

```bash
python main.py
```

Or using uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Environment Variables

- `BOOKS_DB_PATH` - Path to the SQLite database file (default: "books.db")

## API Documentation

Once the server is running, visit:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Example Usage

### Create a book

```bash
curl -X POST "http://localhost:8000/books" \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925}'
```

### List all books

```bash
curl "http://localhost:8000/books"
```

### Filter by author

```bash
curl "http://localhost:8000/books?author=Scott"
```

### Get a single book

```bash
curl "http://localhost:8000/books/1"
```

### Update a book

```bash
curl -X PUT "http://localhost:8000/books/1" \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title"}'
```

### Delete a book

```bash
curl -X DELETE "http://localhost:8000/books/1"
```

### Health check

```bash
curl "http://localhost:8000/health"
```

## Testing

Run the tests:

```bash
python -m pytest tests.py -v
```

## Project Structure

- `main.py` - Main FastAPI application
- `requirements.txt` - Python dependencies
- `tests.py` - Integration tests
- `README.md` - This file

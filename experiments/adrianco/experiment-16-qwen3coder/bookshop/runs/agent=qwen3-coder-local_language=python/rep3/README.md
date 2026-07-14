# Book Collection API

A REST API service for managing a book collection, built with Python, FastAPI, and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- JSON responses with appropriate HTTP status codes

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (supports ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Requirements

- Python 3.7+
- FastAPI
- Uvicorn
- SQLAlchemy

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python main.py
   ```

3. The API will be available at `http://localhost:8000`

## Testing

Run the unit tests:
```bash
python -m pytest tests.py -v
```

## API Usage Examples

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

### Get all books
```bash
curl "http://localhost:8000/books"
```

### Get books by author
```bash
curl "http://localhost:8000/books?author=George%20Orwell"
```

### Get a specific book
```bash
curl "http://localhost:8000/books/1"
```

### Update a book
```bash
curl -X PUT "http://localhost:8000/books/1" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Nineteen Eighty-Four",
    "author": "George Orwell",
    "year": 1948
  }'
```

### Delete a book
```bash
curl -X DELETE "http://localhost:8000/books/1"
```
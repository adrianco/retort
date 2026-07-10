# Book Collection API

A REST API service for managing a book collection, built with FastAPI and SQLite.

## Features

- Create books with title, author, year, and ISBN
- List all books with optional author filtering
- Get a single book by ID
- Update book information
- Delete books
- Health check endpoint

## Requirements

- Python 3.7+
- FastAPI
- Uvicorn (ASGI server)

## Installation

```bash
pip install fastapi uvicorn
```

## Running the Application

```bash
# Run the development server
uvicorn main:app --reload

# Or run with default settings
python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (supports `?author=` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Example Usage

### Create a book
```bash
curl -X POST "http://localhost:8000/books" \
     -H "Content-Type: application/json" \
     -d '{"title": "1984", "author": "George Orwell", "year": 1948, "isbn": "978-0-452-28423-4"}'
```

### List all books
```bash
curl "http://localhost:8000/books"
```

### Get a specific book
```bash
curl "http://localhost:8000/books/1"
```

### Update a book
```bash
curl -X PUT "http://localhost:8000/books/1" \
     -H "Content-Type: application/json" \
     -d '{"title": "Nineteen Eighty-Four", "year": 1948}'
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

Run the tests with:
```bash
python -m pytest tests.py
```
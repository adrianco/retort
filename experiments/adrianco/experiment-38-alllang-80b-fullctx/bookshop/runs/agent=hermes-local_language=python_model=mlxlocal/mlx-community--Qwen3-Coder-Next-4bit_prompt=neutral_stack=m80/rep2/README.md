# Book API REST Service

A REST API service for managing a book collection built with FastAPI and SQLite.

## Features

- Create books (POST /books)
- List all books (GET /books)
- Filter books by author (GET /books?author={author})
- Get a single book by ID (GET /books/{id})
- Update a book (PUT /books/{id})
- Delete a book (DELETE /books/{id})
- Health check endpoint (GET /health)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Example Usage

### Create a book
```bash
curl -X POST "http://localhost:8000/books" \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### List all books
```bash
curl -X GET "http://localhost:8000/books"
```

### Filter by author
```bash
curl -X GET "http://localhost:8000/books?author=George%20Orwell"
```

### Get a single book
```bash
curl -X GET "http://localhost:8000/books/1"
```

### Update a book
```bash
curl -X PUT "http://localhost:8000/books/1" \
  -H "Content-Type: application/json" \
  -d '{"year": 1950}'
```

### Delete a book
```bash
curl -X DELETE "http://localhost:8000/books/1"
```

### Health check
```bash
curl -X GET "http://localhost:8000/health"
```

## Running Tests

```bash
pytest test_api.py -v
```

## Project Structure

- `main.py` - FastAPI application with all endpoints
- `database.py` - SQLAlchemy database models and session management
- `schemas.py` - Pydantic schemas for request/response validation
- `test_api.py` - Integration tests
- `requirements.txt` - Python dependencies

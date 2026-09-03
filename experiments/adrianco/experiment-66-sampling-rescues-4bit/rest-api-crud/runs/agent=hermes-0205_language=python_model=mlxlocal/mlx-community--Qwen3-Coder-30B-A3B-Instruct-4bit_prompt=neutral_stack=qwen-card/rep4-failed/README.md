# Book API REST Service

A REST API service for managing a book collection built with FastAPI and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- SQLite database storage

## Requirements

- Python 3.7+
- FastAPI
- uvicorn
- pydantic

## Installation

1. Clone or download this repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Endpoints

- `GET /health` - Health check endpoint
- `GET /books` - List all books (with optional author filter)
- `GET /books/{id}` - Get a single book by ID
- `POST /books` - Create a new book
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book

## Example Usage

### Create a book:
```bash
curl -X POST "http://localhost:8000/books" \
-H "Content-Type: application/json" \
-d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "9780743273502"}'
```

### Get all books:
```bash
curl "http://localhost:8000/books"
```

### Get a specific book:
```bash
curl "http://localhost:8000/books/1"
```

### Update a book:
```bash
curl -X PUT "http://localhost:8000/books/1" \
-H "Content-Type: application/json" \
-d '{"title": "Updated Title", "author": "Updated Author", "year": 2020, "isbn": "9780743273502"}'
```

### Delete a book:
```bash
curl -X DELETE "http://localhost:8000/books/1"
```
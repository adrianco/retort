# Book API REST Service

A REST API service for managing a book collection using FastAPI and SQLite.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (support ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the server:

```bash
uvicorn main:app --reload
```

The API will be available at http://localhost:8000

## API Documentation

Once the server is running, visit http://localhost:8000/docs to see the interactive API documentation.

## Example Usage

### Create a book

```bash
curl -X POST "http://localhost:8000/books" \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### Get all books

```bash
curl "http://localhost:8000/books"
```

### Get books by author

```bash
curl "http://localhost:8000/books?author=George%20Orwell"
```

### Get a single book

```bash
curl "http://localhost:8000/books/1"
```

### Update a book

```bash
curl -X PUT "http://localhost:8000/books/1" \
  -H "Content-Type: application/json" \
  -d '{"title": "Nineteen Eighty-Four"}'
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

Run the tests with pytest:

```bash
pytest
```

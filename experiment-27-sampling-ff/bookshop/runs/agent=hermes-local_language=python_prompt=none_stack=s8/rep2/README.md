# Book Collection REST API

A simple REST API service for managing a book collection, built with Flask and SQLite.

## Features

- **POST /books** - Create a new book
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Setup

1. Ensure Python 3.9+ is installed
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Service

```bash
python app.py
```

The API will be available at `http://localhost:5000`

## Usage Examples

### Create a book
```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### List all books
```bash
curl http://localhost:5000/books
```

### List books by author
```bash
curl "http://localhost:5000/books?author=Fitzgerald"
```

### Get a single book
```bash
curl http://localhost:5000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby (Updated)", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:5000/books/1
```

### Health check
```bash
curl http://localhost:5000/health
```

## Testing

Run the test suite:

```bash
pytest tests.py -v
```

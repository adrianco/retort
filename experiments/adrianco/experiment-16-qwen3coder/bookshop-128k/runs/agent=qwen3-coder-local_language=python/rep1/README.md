# Book Collection REST API

A simple REST API service for managing a book collection.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- SQLite database storage

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (with optional `?author=` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Requirements

- Python 3
- Flask
- SQLite (built-in with Python)

## Setup

1. Clone the repository
2. Install dependencies (Flask is included with Python, but you can install it explicitly with `pip install Flask` if needed)
3. Run the application: `python app.py`

## Usage Examples

### Create a book
```bash
curl -X POST http://localhost:5000/books \
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
curl http://localhost:5000/books
```

### Get books by author
```bash
curl http://localhost:5000/books?author=Orwell
```

### Get a specific book
```bash
curl http://localhost:5000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "1984",
    "author": "George Orwell",
    "year": 1949,
    "isbn": "978-0-452-28423-4"
  }'
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

Run unit tests with:
```bash
python test_app.py
```
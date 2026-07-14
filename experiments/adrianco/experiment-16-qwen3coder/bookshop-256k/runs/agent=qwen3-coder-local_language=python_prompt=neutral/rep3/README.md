# Book Collection REST API

A simple REST API service for managing a book collection with SQLite backend.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- SQLite database storage

## Endpoints

### Health Check
- `GET /health` - Returns health status

### Books Management
- `POST /books` - Create a new book
- `GET /books` - List all books (supports `?author=` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book

## Requirements

- Python 3.6+
- Flask
- aiosqlite

## Setup

1. Install dependencies:
   ```bash
   pip install flask aiosqlite
   ```

2. Run the application:
   ```bash
   python app.py
   ```

3. The API will be available at `http://localhost:5000`

## Usage Examples

### Create a book
```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "1984",
    "author": "George Orwell",
    "year": 1948,
    "isbn": "978-0451524935"
  }'
```

### Get all books
```bash
curl http://localhost:5000/books
```

### Get books by author
```bash
curl http://localhost:5000/books?author=George%20Orwell
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
    "title": "Nineteen Eighty-Four",
    "author": "George Orwell",
    "year": 1948,
    "isbn": "978-0451524935"
  }'
```

### Delete a book
```bash
curl -X DELETE http://localhost:5000/books/1
```
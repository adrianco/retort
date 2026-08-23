# Book API REST Service

A REST API service for managing a book collection built with Flask and SQLite.

## Features

- Create books (POST /books)
- List all books (GET /books) with optional author filter
- Get a single book by ID (GET /books/{id})
- Update a book (PUT /books/{id})
- Delete a book (DELETE /books/{id})
- Health check endpoint (GET /health)

## Requirements

- Python 3.7+
- Flask
- SQLite (included with Python standard library)

## Setup

1. Clone or copy the project files to your working directory

2. Install dependencies:
```bash
pip install flask
```

3. Run the application:
```bash
python app.py
```

The server will start on `http://localhost:5000`

## API Endpoints

### Health Check
```http
GET /health
```
Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

### List Books
```http
GET /books
GET /books?author=AuthorName
```

### Get Book by ID
```http
GET /books/{id}
```

### Create Book
```http
POST /books
Content-Type: application/json

{
  "title": "Book Title",
  "author": "Author Name",
  "year": 2024,
  "isbn": "978-0-123456-78-9"
}
```

### Update Book
```http
PUT /books/{id}
Content-Type: application/json

{
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 2025
}
```

### Delete Book
```http
DELETE /books/{id}
```

## Input Validation

- `title` and `author` are required fields
- All fields must be strings (except year which must be an integer)
- Year must be between 0 and 9999

## Testing

Run the tests with pytest:
```bash
pip install pytest
pytest test_app.py -v
```

## Example Usage

### Create a book
```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949}'
```

### List all books
```bash
curl http://localhost:5000/books
```

### List books by author
```bash
curl "http://localhost:5000/books?author=George Orwell"
```

### Get a book by ID
```bash
curl http://localhost:5000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"year": 1950}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:5000/books/1
```

### Health check
```bash
curl http://localhost:5000/health
```

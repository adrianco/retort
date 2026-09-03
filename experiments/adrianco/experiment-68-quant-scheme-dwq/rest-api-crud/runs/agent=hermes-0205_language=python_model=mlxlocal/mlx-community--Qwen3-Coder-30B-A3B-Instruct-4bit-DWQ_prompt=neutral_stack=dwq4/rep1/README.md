# Book API REST Service

A REST API service for managing a book collection with CRUD operations.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- SQLite database storage
- JSON responses with appropriate HTTP status codes
- Input validation

## Endpoints

- `POST /books` - Create a new book (requires title and author)
- `GET /books` - List all books (supports ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the application:
   ```
   python app.py
   ```

3. The API will be available at `http://localhost:5000`

## Testing

Run tests with:
```
python -m pytest test_app.py -v
```

## Example Usage

### Create a book
```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0-7432-7356-5"}'
```

### Get all books
```bash
curl http://localhost:5000/books
```

### Get books by author
```bash
curl http://localhost:5000/books?author=F. Scott Fitzgerald
```

### Get a specific book
```bash
curl http://localhost:5000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby - Revised", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0-7432-7356-5"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:5000/books/1
```
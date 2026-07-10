# Book Collection REST API

A simple REST API service for managing a book collection with SQLite backend.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- JSON responses with appropriate HTTP status codes
- Input validation

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (support ?author= filter)
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

The API can be tested with curl or any HTTP client.

Example requests:
```
# Create a book
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1948, "isbn": "978-0-452-28423-4"}'

# Get all books
curl http://localhost:5000/books

# Get books by author
curl http://localhost:5000/books?author=Orwell

# Get a specific book
curl http://localhost:5000/books/1

# Update a book
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1948}'

# Delete a book
curl -X DELETE http://localhost:5000/books/1
```

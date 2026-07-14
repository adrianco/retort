# Book Collection REST API

A simple REST API service for managing a book collection, built with Flask and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- JSON responses with appropriate HTTP status codes
- Input validation

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (supports ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Setup

1. Install dependencies:
   ```bash
   pip install flask flask-sqlalchemy
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
  -d '{"title": "1984", "author": "George Orwell", "year": 1948, "isbn": "978-0-452-28423-4"}'
```

### List all books
```bash
curl http://localhost:5000/books
```

### Get a specific book
```bash
curl http://localhost:5000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Nineteen Eighty-Four", "year": 1948}'
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

Run the tests with:
```bash
python test_app.py
```
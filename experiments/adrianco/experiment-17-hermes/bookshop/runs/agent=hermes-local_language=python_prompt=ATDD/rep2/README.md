# Book API REST Service

A REST API service for managing a book collection with SQLite storage.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (with optional author filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Setup

1. Install Python 3.7+
2. Install dependencies:
   ```bash
   pip install flask flask-sqlalchemy
   ```
3. Run the application:
   ```bash
   python app.py
   ```

## Testing

Run tests with:
```bash
python test_app.py
```

## Usage Examples

### Create a book
```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1948, "isbn": "978-0-452-28423-4"}'
```

### Get all books
```bash
curl http://localhost:5000/books
```

### Get books by author
```bash
curl http://localhost:5000/books?author=George%20Orwell
```

### Get a single book
```bash
curl http://localhost:5000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1948, "isbn": "978-0-452-28423-4"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:5000/books/1
```

### Health check
```bash
curl http://localhost:5000/health
```

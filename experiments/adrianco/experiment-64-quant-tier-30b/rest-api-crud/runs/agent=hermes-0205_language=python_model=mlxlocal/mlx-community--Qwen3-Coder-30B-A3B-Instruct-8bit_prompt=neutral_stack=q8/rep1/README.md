# Book API REST Service

A REST API service for managing a book collection with CRUD operations.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- SQLite database for persistent storage
- JSON responses with appropriate HTTP status codes
- Input validation

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (with optional `author` filter)
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

## Usage Examples

### Create a book
```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1948, "isbn": "978-0451524935"}'
```

### Get all books
```bash
curl http://localhost:5000/books
```

### Get books by author
```bash
curl http://localhost:5000/books?author=Orwell
```

### Get a single book
```bash
curl http://localhost:5000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1948, "isbn": "978-0451524935"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:5000/books/1
```

## Testing

Run the tests with:
```bash
python -m pytest test_app.py -v
```

## Implementation Details

This implementation uses:
- Flask for the web framework
- SQLite for data persistence
- Plain SQLite (no ORM) for simplicity
- JSON responses with appropriate HTTP status codes
- Input validation for required fields
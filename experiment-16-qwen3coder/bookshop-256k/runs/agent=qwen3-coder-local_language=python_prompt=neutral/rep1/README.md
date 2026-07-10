# Book Collection REST API

A simple REST API for managing a book collection with SQLite database.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- JSON responses with appropriate HTTP status codes
- Embedded SQLite database

## Endpoints

- `POST /books` - Create a new book (title, author, year, isbn)
- `GET /books` - List all books (support ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Requirements

- Python 3.x
- Flask
- SQLite (built-in with Python)

## Setup

1. Install Python 3.x
2. Run the application: `python app.py`

The API will be available at `http://localhost:5001`

## Usage Examples

### Create a book
```bash
curl -X POST http://localhost:5001/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1948, "isbn": "9780451524935"}'
```

### Get all books
```bash
curl -X GET http://localhost:5001/books
```

### Get books by author
```bash
curl -X GET http://localhost:5001/books?author=Orwell
```

### Get a specific book
```bash
curl -X GET http://localhost:5001/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:5001/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1948, "isbn": "9780451524935"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:5001/books/1
```

### Health check
```bash
curl -X GET http://localhost:5001/health
```

## Testing

The application includes unit tests that verify all functionality. The tests can be run with:

```bash
python3 simple_test.py
```

Or manually by:
1. Starting the server: `python3 app.py`
2. Using curl commands to test each endpoint as shown above
3. Stopping the server when finished

## Database

The application uses SQLite database (`books.db`) to store book data. The database is automatically created when the application starts.
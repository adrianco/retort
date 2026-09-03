# Book API REST Service

A simple REST API service for managing a book collection built with Flask and SQLite.

## Features

- Create, read, update, and delete books
- Health check endpoint
- Filtering by author
- Input validation and error handling
- SQLite database storage

## Requirements

- Python 3.6+
- Flask

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```
   python app.py
   ```

2. The API will be available at `http://localhost:5000`

## API Endpoints

### Health Check
- GET `/health` - Returns health status

### Books Management
- POST `/books` - Create a new book
- GET `/books` - List all books (with optional author filter)
- GET `/books/{id}` - Get a single book by ID
- PUT `/books/{id}` - Update a book by ID
- DELETE `/books/{id}` - Delete a book by ID

## Example Usage

### Create a book
```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### Get all books
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
  -d '{"title": "Updated Title", "author": "Updated Author", "year": 2020}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:5000/books/1
```

## Testing

To run tests:
```bash
python -m pytest test_app.py -v
```

## Database

The application uses SQLite to store book data in a file called `books.db` in the current directory.

## License

MIT License
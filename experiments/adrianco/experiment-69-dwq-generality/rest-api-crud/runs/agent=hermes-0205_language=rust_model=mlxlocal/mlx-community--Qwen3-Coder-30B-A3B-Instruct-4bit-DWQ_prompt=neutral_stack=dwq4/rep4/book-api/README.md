# Book API REST Service

This is a Python-based REST API service for managing a book collection. It provides endpoints for creating, reading, updating, and deleting books, with SQLite as the database backend.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (support ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Requirements

- Python 3.7+
- Flask
- SQLite (built-in)

## Setup

1. Clone this repository
2. Navigate to the project directory
3. Install dependencies:
   ```bash
   pip install flask
   ```
4. Run the server:
   ```bash
   python app.py
   ```

## Usage

1. Start the server:
   ```bash
   python app.py
   ```

2. The server will run on `http://127.0.0.1:8080`

## Testing

Run tests with:
```bash
python -m pytest tests.py
```

## API Endpoints

### Create a new book
```bash
curl -X POST http://127.0.0.1:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'
```

### Get all books
```bash
curl http://127.0.0.1:8080/books
```

### Get books by author
```bash
curl http://127.0.0.1:8080/books?author=F. Scott Fitzgerald
```

### Get a book by ID
```bash
curl http://127.0.0.1:8080/books/1
```

### Update a book
```bash
curl -X PUT http://127.0.0.1:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1926,"isbn":"978-0-7432-7356-5"}'
```

### Delete a book
```bash
curl -X DELETE http://127.0.0.1:8080/books/1
```

### Health check
```bash
curl http://127.0.0.1:8080/health
```

## Database

The application uses an SQLite database file called `books.db` in the project directory to store book information.

## License

MIT License
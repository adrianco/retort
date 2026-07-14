# Book Collection REST API

A simple REST API for managing a book collection with CRUD operations.

## Features

- Create books (POST /books)
- List all books or filter by author (GET /books)
- Get a single book by ID (GET /books/{id})
- Update a book (PUT /books/{id})
- Delete a book (DELETE /books/{id})
- Health check endpoint (GET /health)

## Requirements

- Python 3.7+
- Flask
- Flask-SQLAlchemy

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python app.py
   ```

3. The API will be available at `http://localhost:5000`

## API Endpoints

### Health Check
- `GET /health` - Check if the service is running

### Books Management
- `POST /books` - Create a new book
- `GET /books` - List all books (supports ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book

## Example Usage

### Create a book
```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "1984",
    "author": "George Orwell",
    "year": 1948,
    "isbn": "978-0-452-28423-4"
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
    "year": 1948
  }'
```

### Delete a book
```bash
curl -X DELETE http://localhost:5000/books/1
```

## Testing

Run the tests with:
```bash
python -m pytest tests.py
```

## Database

The application uses SQLite for data persistence. The database file `books.db` will be created in the project directory.
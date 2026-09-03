# Book Collection REST API

A simple REST API service for managing a book collection with SQLite database storage.

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
- Flask-SQLAlchemy

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

## API Endpoints

### Health Check
```
GET /health
```

### Create Book
```
POST /books
Content-Type: application/json

{
    "title": "Book Title",
    "author": "Author Name",
    "year": 2023,
    "isbn": "1234567890"
}
```

### List Books
```
GET /books
GET /books?author=Author%20Name
```

### Get Book by ID
```
GET /books/1
```

### Update Book
```
PUT /books/1
Content-Type: application/json

{
    "title": "Updated Book Title",
    "author": "Updated Author Name",
    "year": 2024,
    "isbn": "0987654321"
}
```

### Delete Book
```
DELETE /books/1
```

## Testing

Run the tests using:
```bash
python test_app.py
```

## Database

The application uses an SQLite database (`books.db`) to store book information. The database is automatically created when the application starts.
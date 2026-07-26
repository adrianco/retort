# Book Collection REST API Service

A REST API service for managing a book collection using Python, Flask, and SQLite.

## Features

- Create books with title, author, year, and ISBN
- List all books with optional author filter
- Get a single book by ID
- Update book information
- Delete books
- Health check endpoint

## Requirements

- Python 3.11+
- Flask
- SQLite (included with Python standard library)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python app.py
```

The server will start on `http://localhost:5000`

## API Endpoints

### Health Check
```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00"
}
```

### Create Book
```
POST /books
Content-Type: application/json

{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

Response: `201 Created`

### List Books
```
GET /books
```

With author filter:
```
GET /books?author=Fitzgerald
```

Response: `200 OK`

### Get Book by ID
```
GET /books/{id}
```

Response: `200 OK` or `404 Not Found`

### Update Book
```
PUT /books/{id}
Content-Type: application/json

{
  "title": "Updated Title"
}
```

Response: `200 OK` or `404 Not Found`

### Delete Book
```
DELETE /books/{id}
```

Response: `200 OK` or `404 Not Found`

## Running Tests

```bash
python -m pytest test_app.py -v
```

## Project Structure

- `app.py` - Main Flask application
- `test_app.py` - Integration tests
- `requirements.txt` - Python dependencies
- `books.db` - SQLite database (created automatically)

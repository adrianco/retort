# Book Collection REST API

A simple REST API for managing a book collection using Flask and SQLite.

## Features

- Create books (POST /books)
- List all books (GET /books) with optional author filter
- Get a single book by ID (GET /books/{id})
- Update a book (PUT /books/{id})
- Delete a book (DELETE /books/{id})
- Health check endpoint (GET /health)

## Requirements

- Python 3.6+
- Flask

## Setup

1. Clone or download this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the Application

```
python app.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### Health Check
```
GET /health
```

### Create a Book
```
POST /books
Content-Type: application/json

{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
}
```

### List Books
```
GET /books
```

To filter by author:
```
GET /books?author=Fitzgerald
```

### Get a Book by ID
```
GET /books/1
```

### Update a Book
```
PUT /books/1
Content-Type: application/json

{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
}
```

### Delete a Book
```
DELETE /books/1
```

## Testing

Run the tests with:
```
python -m pytest tests.py
```

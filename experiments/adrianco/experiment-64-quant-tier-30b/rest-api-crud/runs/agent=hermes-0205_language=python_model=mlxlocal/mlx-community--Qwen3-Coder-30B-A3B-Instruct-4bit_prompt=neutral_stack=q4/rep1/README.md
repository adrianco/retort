# Book API REST Service

A simple REST API service for managing a book collection.

## Features
- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- SQLite database storage

## Requirements
- Python 3.6+
- Flask
- SQLite (included with Python)

## Installation
```bash
pip install -r requirements.txt
```

## Usage
Start the server:
```bash
python app.py
```

The API will be available at http://localhost:5000

## API Endpoints

### Health Check
GET /health

### Create a Book
POST /books

Request body:
```json
{
    "title": "Book Title",
    "author": "Author Name",
    "year": 2023,
    "isbn": "1234567890"
}
```

### Get All Books
GET /books

### Get a Book by ID
GET /books/{id}

### Update a Book
PUT /books/{id}

Request body:
```json
{
    "title": "Updated Book Title",
    "author": "Updated Author Name",
    "year": 2024,
    "isbn": "0987654321"
}
```

### Delete a Book
DELETE /books/{id}

## Testing
Run tests:
```bash
python test_app.py
```

## Database
Data is stored in SQLite database file `books.db` in the current directory.
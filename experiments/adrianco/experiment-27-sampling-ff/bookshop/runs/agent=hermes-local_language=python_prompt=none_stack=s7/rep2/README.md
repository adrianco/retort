# Book API REST Service

A REST API service for managing a book collection, built with Python and Flask.

## Requirements

- Python 3.11+
- Flask
- Pytest (for testing)

## Installation

1. Install dependencies:

```bash
pip install flask pytest
```

## Running the Application

```bash
python app.py
```

The API will be available at `http://localhost:5000`.

## API Endpoints

| Method   | Endpoint         | Description                        |
|----------|------------------|------------------------------------|
| GET      | /health          | Health check endpoint              |
| POST     | /books           | Create a new book                  |
| GET      | /books           | List all books (optional ?author=) |
| GET      | /books/{id}      | Get a single book by ID            |
| PUT      | /books/{id}      | Update a book                      |
| DELETE   | /books/{id}      | Delete a book                      |

### Create a Book (POST /books)

Request body (JSON):

```json
{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
}
```

- `title` and `author` are required.
- `year` and `isbn` are optional.

### List Books (GET /books)

Returns all books. Optionally filter by author:

```
GET /books?author=Orwell
```

### Get a Book (GET /books/{id})

Returns a single book by its ID. Returns 404 if not found.

### Update a Book (PUT /books/{id})

Request body (JSON) with fields to update. `title` and `author` are required in the request body.

### Delete a Book (DELETE /books/{id})

Deletes a book by ID. Returns 404 if not found.

## Database

Data is stored in a SQLite database file (`books.db`) created in the project directory.

## Running Tests

```bash
python -m pytest test_app.py -v
```

12 acceptance tests covering:
- Health check endpoint
- Creating books (success and validation errors)
- Listing all books and filtering by author
- Getting a single book by ID
- Updating a book
- Deleting a book
- Proper 404 handling for non-existent books

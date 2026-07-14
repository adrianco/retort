# Book API REST Service

A REST API service for managing a book collection, built with Python and Flask.

## Features

- **CRUD Operations**: Create, Read, Update, and Delete books
- **Filtering**: Filter books by author name
- **Validation**: Input validation for required fields
- **SQLite Backend**: Data stored in an embedded SQLite database
- **JSON Responses**: All responses are in JSON format

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| POST | /books | Create a new book |
| GET | /books | List all books (optional: ?author=filter) |
| GET | /books/{id} | Get a single book by ID |
| PUT | /books/{id} | Update a book |
| DELETE | /books/{id} | Delete a book |

### Request/Response Examples

#### Create a Book
```
POST /books
Content-Type: application/json

{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
}

Response: 201 Created
{
    "id": 1,
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
}
```

#### List Books
```
GET /books
GET /books?author=Orwell
```

#### Update a Book
```
PUT /books/1
Content-Type: application/json

{
    "title": "The Great Gatsby (Updated Edition)"
}

Response: 200 OK
{
    "id": 1,
    "title": "The Great Gatsby (Updated Edition)",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
}
```

## Setup and Run

### Prerequisites

- Python 3.8 or higher

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

The server will start at `http://localhost:5000`.

### Running Tests

```bash
pip install -r requirements.txt
pytest test_app.py -v
```

## Project Structure

```
app.py            - Main Flask application with all API endpoints
test_app.py       - Comprehensive test suite
requirements.txt  - Python dependencies
README.md         - This file
```

## Error Responses

All error responses follow this format:
```json
{
    "error": "Description of the error"
}
```

Common status codes:
- `200` - Success
- `201` - Created (new book)
- `400` - Bad Request (validation error)
- `404` - Not Found (book doesn't exist)

# Book API - Python REST Service

A REST API service for managing a book collection implemented in Python with Flask and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- JSON responses with appropriate HTTP status codes
- SQLite database storage

## Endpoints

- `POST /books` - Create a new book (title, author, year, isbn)
- `GET /books` - List all books (support ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Setup

1. Install Python 3.6+
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

```bash
python app.py
```

The API will be available at `http://localhost:8080`

## Testing

The application includes unit tests. Run them with:
```bash
python -m pytest tests.py -v
```

## Database

The application uses SQLite and creates a `books.db` file in the working directory to store book data.
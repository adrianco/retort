# Book API REST Service

A REST API service for managing a book collection with CRUD operations.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- SQLite database storage
- Input validation
- JSON responses with appropriate HTTP status codes

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (with optional `author` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

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

## Testing

The application includes unit and integration tests. To run them:

```bash
python -m pytest test_app.py -v
```

## Database

The application uses SQLite for data storage. The database file `books.db` will be created in the working directory.

## Requirements

- Python 3.6+
- Flask
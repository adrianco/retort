# Book Collection REST API

A REST API service for managing a book collection, built with Flask and SQLite.

## Features

- **Create** books with title, author, year, and isbn
- **List** all books with optional author filtering
- **Get** a single book by ID
- **Update** an existing book
- **Delete** a book
- **Health check** endpoint for monitoring

## Setup

1. Create and activate a virtual environment (if not already done):

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install flask
   ```

3. Run the application:

   ```bash
   python app.py
   ```

   The server will start at `http://localhost:5000`.

## Running Tests

```bash
pytest test_app.py -v
```

## API Endpoints

### GET /health

Health check endpoint.

**Response:**
```json
{"status": "healthy"}
```

### POST /books

Create a new book.

**Request body (JSON):**
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

**Response (201 Created):**
```json
{"id": 1, "title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}
```

### GET /books

List all books. Supports optional `?author=Name` filter for partial matching.

**Response (200 OK):**
```json
[
  {"id": 1, "title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}
]
```

### GET /books/{id}

Get a single book by ID.

**Response (200 OK):**
```json
{"id": 1, "title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}
```

**Response (404 Not Found):**
```json
{"error": "Book not found"}
```

### PUT /books/{id}

Update an existing book. Only provided fields are updated.

**Response (200 OK):**
```json
{"id": 1, "title": "Updated Title", "author": "Updated Author", "year": 1925, "isbn": "978-0743273565"}
```

### DELETE /books/{id}

Delete a book.

**Response (200 OK):**
```json
{"message": "Book deleted"}
```

## Database

Data is stored in a SQLite database file (`books.db`) in the project root. The database is created automatically on first run.

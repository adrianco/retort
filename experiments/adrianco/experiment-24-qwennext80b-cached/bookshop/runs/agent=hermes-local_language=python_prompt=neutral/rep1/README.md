# Book API REST Service

A REST API service for managing a book collection using Flask and SQLite.

## Features

- Create books with title, author, year, and ISBN
- List all books with optional author filter
- Get a single book by ID
- Update book information
- Delete books
- Health check endpoint

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Running the Server

```bash
python app.py
```

The server will start on `http://localhost:5000`.

### Environment Variables

- `PORT` - Port to run the server on (default: 5000)
- `DEBUG` - Enable debug mode (default: false)
- `BOOK_API_DATABASE` - Path to SQLite database file (default: books.db)

## API Endpoints

### Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00.000000Z"
}
```

### List Books

```
GET /books
GET /books?author={author_name}
```

### Get Book

```
GET /books/{id}
```

### Create Book

```
POST /books
Content-Type: application/json

{
  "title": "Book Title",
  "author": "Author Name",
  "year": 2024,
  "isbn": "123-4567890123"
}
```

### Update Book

```
PUT /books/{id}
Content-Type: application/json

{
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 2024
}
```

### Delete Book

```
DELETE /books/{id}
```

## Tests

Run the test suite:

```bash
python test_app.py
```

## Project Structure

- `app.py` - Main Flask application
- `test_app.py` - Unit and integration tests
- `requirements.txt` - Python dependencies
- `README.md` - This file

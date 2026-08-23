# Book Collection REST API Service

A REST API service for managing a book collection using Flask and SQLite.

## Features

- **Health Check**: `GET /health`
- **Create Book**: `POST /books`
- **List Books**: `GET /books` (with optional `?author=` filter)
- **Get Book**: `GET /books/{id}`
- **Update Book**: `PUT /books/{id}`
- **Delete Book**: `DELETE /books/{id}`

## Installation

1. Ensure you have Python 3.7 or higher installed.

2. Install the required dependencies:

```bash
pip install flask
```

Or with a requirements file:

```bash
pip install -r requirements.txt
```

## Running the Server

Start the server:

```bash
python app.py
```

The API will be available at `http://localhost:5000`.

## API Endpoints

### Health Check

```bash
curl http://localhost:5000/health
```

Response:
```json
{"status": "healthy"}
```

### List All Books

```bash
curl http://localhost:5000/books
```

### List Books by Author

```bash
curl "http://localhost:5000/books?author=John Doe"
```

### Create a Book

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### Get a Book by ID

```bash
curl http://localhost:5000/books/1
```

### Update a Book

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby (Updated)", "year": 1926}'
```

### Delete a Book

```bash
curl -X DELETE http://localhost:5000/books/1
```

## Database

The application uses SQLite to store book data. The database file is named `books.db` and is created automatically in the same directory as `app.py` when the server starts.

## Validation

The API includes input validation:

- `title` and `author` are required fields
- `title` and `author` must be non-empty strings
- `year` must be a valid integer (0-9999) if provided
- `isbn` must be a string if provided

## Testing

Run the tests:

```bash
python -m unittest discover tests
```

Or:

```bash
python tests/test_api.py
```

## Project Structure

```
.
├── app.py           # Main Flask application
├── books.db         # SQLite database (created at runtime)
├── requirements.txt # Dependencies
├── README.md        # This file
└── tests/
    └── test_api.py  # Integration tests
```

## License

MIT License

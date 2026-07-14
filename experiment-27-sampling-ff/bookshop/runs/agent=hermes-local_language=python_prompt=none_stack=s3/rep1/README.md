# Book API REST Service

A REST API service for managing a book collection, built with Flask and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation with proper error handling
- SQLite database for persistent storage
- Health check endpoint

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

## API Endpoints

| Method | Endpoint          | Description                  |
|--------|-------------------|------------------------------|
| POST   | /books            | Create a new book            |
| GET    | /books            | List all books               |
| GET    | /books/{id}       | Get a single book by ID      |
| PUT    | /books/{id}       | Update a book                |
| DELETE | /books/{id}       | Delete a book                |
| GET    | /health           | Health check                 |

## Request/Response Examples

### Create a Book
```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'
```

### List All Books
```bash
curl http://localhost:5000/books
```

### Filter by Author
```bash
curl "http://localhost:5000/books?author=Orwell"
```

### Get a Book by ID
```bash
curl http://localhost:5000/books/1
```

### Update a Book
```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Nineteen Eighty-Four"}'
```

### Delete a Book
```bash
curl -X DELETE http://localhost:5000/books/1
```

## Testing

Run the test suite:

```bash
pytest test_app.py -v
```

## Validation Rules

- `title` and `author` are required fields (non-empty strings)
- `year` must be an integer if provided
- `isbn` must be unique across all books

## Error Responses

All error responses return a JSON body with an `error` field and the appropriate HTTP status code:

- 400 — Bad request (missing fields, invalid data)
- 404 — Resource not found
- 409 — Conflict (duplicate ISBN)

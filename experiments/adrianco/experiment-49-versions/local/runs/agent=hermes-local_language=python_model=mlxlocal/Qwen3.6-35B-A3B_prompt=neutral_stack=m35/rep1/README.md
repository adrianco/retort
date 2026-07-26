# Book Collection REST API

A REST API service for managing a book collection, built with Flask and SQLite.

## Endpoints

| Method | Endpoint        | Description                    |
|--------|-----------------|--------------------------------|
| POST   | /books          | Create a new book              |
| GET    | /books          | List all books (optional ?author= filter) |
| GET    | /books/{id}     | Get a single book by ID        |
| PUT    | /books/{id}     | Update a book                  |
| DELETE | /books/{id}     | Delete a book                  |
| GET    | /health         | Health check                   |

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the application:

```bash
python app.py
```

The API will be available at `http://localhost:5000`.

## Usage Examples

### Create a book

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### List all books

```bash
curl http://localhost:5000/books
```

### List books by author

```bash
curl "http://localhost:5000/books?author=Fitzgerald"
```

### Get a book by ID

```bash
curl http://localhost:5000/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby (Updated)", "author": "F. Scott Fitzgerald"}'
```

### Delete a book

```bash
curl -X DELETE http://localhost:5000/books/1
```

### Health check

```bash
curl http://localhost:5000/health
```

## Testing

Run the test suite:

```bash
pytest test_app.py -v
```

## API Response Format

All responses are JSON. Successful responses return the resource or a success message. Error responses include an "error" field.

HTTP Status Codes:
- 200: Success
- 201: Created
- 400: Bad Request (validation error)
- 404: Not Found
- 500: Internal Server Error

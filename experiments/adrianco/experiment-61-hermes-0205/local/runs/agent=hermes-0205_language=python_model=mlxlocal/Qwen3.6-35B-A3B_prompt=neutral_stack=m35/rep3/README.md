# Book Collection REST API

A REST API service for managing a book collection, built with Flask and SQLite.

## Endpoints

| Method | Endpoint          | Description                        |
|--------|-------------------|------------------------------------|
| GET    | /health           | Health check                       |
| POST   | /books            | Create a new book                  |
| GET    | /books            | List all books (optional ?author=) |
| GET    | /books/{id}       | Get a single book by ID            |
| PUT    | /books/{id}       | Update a book                      |
| DELETE | /books/{id}       | Delete a book                      |

## Setup

1. Install dependencies:

```
pip install flask pytest
```

2. Run the application:

```
python app.py
```

The API will be available at http://localhost:5000

## Running Tests

```
python -m pytest test_app.py -v
```

## Example Requests

Create a book:

```
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'
```

List all books:

```
curl http://localhost:5000/books
```

List books by author:

```
curl "http://localhost:5000/books?author=Orwell"
```

Get a single book:

```
curl http://localhost:5000/books/1
```

Update a book:

```
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Nineteen Eighty-Four", "author": "George Orwell"}'
```

Delete a book:

```
curl -X DELETE http://localhost:5000/books/1
```

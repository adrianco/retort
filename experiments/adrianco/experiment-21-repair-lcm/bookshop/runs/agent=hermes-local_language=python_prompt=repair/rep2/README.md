# Book Collection REST API

A REST API service for managing a collection of books, built with Flask and SQLite.

## Requirements

- Python 3.11+
- Flask

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. (Optional) Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
```

## Running the Service

```bash
python app.py
```

The server will start on `http://0.0.0.0:5000`.

## API Endpoints

| Method | Endpoint          | Description                      |
|--------|-------------------|----------------------------------|
| GET    | /health           | Health check endpoint            |
| POST   | /books            | Create a new book                |
| GET    | /books            | List all books (supports ?author= filter) |
| GET    | /books/{id}       | Get a single book by ID          |
| PUT    | /books/{id}       | Update an existing book          |
| DELETE | /books/{id}       | Delete a book                    |

### Create a Book (POST /books)

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}'
```

- `title` and `author` are required. `year` and `isbn` are optional.

### List Books (GET /books)

```bash
# List all books
curl http://localhost:5000/books

# Filter by author
curl "http://localhost:5000/books?author=George%20Orwell"
```

### Get a Book (GET /books/{id})

```bash
curl http://localhost:5000/books/1
```

### Update a Book (PUT /books/{id})

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "1984 (Updated Edition)"}'
```

Only the fields you provide are updated; others remain unchanged.

### Delete a Book (DELETE /books/{id})

```bash
curl -X DELETE http://localhost:5000/books/1
```

## Running Tests

```bash
pytest test_app.py -v
```

There are 15 tests covering all endpoints, including validation, filtering, and error cases.

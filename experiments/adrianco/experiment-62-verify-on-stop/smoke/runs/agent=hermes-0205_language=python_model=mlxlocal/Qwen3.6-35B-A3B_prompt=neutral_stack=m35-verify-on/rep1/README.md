# Book API REST Service

A REST API service for managing a book collection, built with Flask and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Setup and Run

### 1. Create a virtual environment (if not already created)

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install flask flask-sqlalchemy
```

### 3. Run the application

```bash
python app.py
```

The API will be available at `http://localhost:5000`.

## API Usage Examples

### Create a book

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "9780743273565"}'
```

### List all books

```bash
curl http://localhost:5000/books
```

### List books filtered by author

```bash
curl "http://localhost:5000/books?author=Fitzgerald"
```

### Get a single book

```bash
curl http://localhost:5000/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title"}'
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

### Test coverage

Run with coverage report:

```bash
pytest test_app.py -v --cov=app --cov-report=term-missing
```

## Technical Details

- **Framework**: Flask
- **Database**: SQLite (embedded, no external server required)
- **Validation**: Title and author are required fields; empty strings are rejected
- **Error handling**: Proper HTTP status codes (200, 201, 400, 404)

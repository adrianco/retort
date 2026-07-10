# Book API REST Service

A REST API for managing a book collection, built with Flask and SQLAlchemy, backed by SQLite.

## Requirements

- Python 3.10+
- pip

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

## API Endpoints

| Method | Endpoint           | Description                      |
|--------|--------------------|----------------------------------|
| GET    | /health            | Health check                     |
| POST   | /books             | Create a new book                |
| GET    | /books             | List all books (optional ?author= filter) |
| GET    | /books/<id>        | Get a single book by ID          |
| PUT    | /books/<id>        | Update a book                    |
| DELETE | /books/<id>        | Delete a book                    |

### POST /books

Create a new book.

Request body (JSON):

```json
{
  "title": "1984",
  "author": "George Orwell",
  "year": 1949,
  "isbn": "978-0451524935"
}
```

- `title` (required): The book title
- `author` (required): The book author
- `year` (optional): Publication year
- `isbn` (optional): ISBN string

Response: 201 Created with the created book object.

### GET /books

List all books. Supports optional query parameter `?author=<name>` to filter by author (case-insensitive partial match).

Response: 200 OK with an array of book objects.

### GET /books/<id>

Get a single book by its ID.

Response: 200 OK with the book object, or 404 if not found.

### PUT /books/<id>

Update an existing book. All fields except `id` are optional. When updating, `title` and `author` must not be empty.

Response: 200 OK with the updated book object, or 404 if the book does not exist.

### DELETE /books/<id>

Delete a book by ID.

Response: 200 OK with a confirmation message, or 404 if the book does not exist.

## Health Check

| Method | Endpoint  | Description           |
|--------|-----------|-----------------------|
| GET    | /health   | Returns 200 with `{"status": "healthy"}` |

## Testing

Run the full test suite:

```bash
pytest tests/ -v
```

The suite includes:

- **Acceptance tests** (tests/test_acceptance.py) — 27 scenarios exercising all REST endpoints from an external client perspective
- **Unit tests** (tests/test_unit.py) — 5 tests covering model validation, the Book model, and factory function

Each test scenario starts from a clean, empty database.

## Architecture

- Flask application factory pattern (`create_app()`)
- SQLAlchemy ORM with SQLite backend
- In-memory SQLite (`sqlite://`) for testing
- RESTful design with proper HTTP status codes (201, 200, 400, 404)

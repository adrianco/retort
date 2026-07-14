# Book Collection REST API

A REST API service for managing a book collection, built with Flask and SQLite.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the API:

```bash
python app.py
```

The server will start at http://localhost:5000

## Endpoints

| Method | Path          | Description                     |
|--------|---------------|---------------------------------|
| GET    | /health       | Health check                    |
| POST   | /books        | Create a new book               |
| GET    | /books        | List all books (optionally filter by author) |
| GET    | /books/{id}   | Get a single book by ID         |
| PUT    | /books/{id}   | Update a book                   |
| DELETE | /books/{id}   | Delete a book                   |

### Book fields

- **title** (required, string): The book title
- **author** (required, string): The book author
- **year** (optional, integer): Publication year
- **isbn** (optional, string): ISBN number

### Examples

Create a book:

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"1984\",\"author\":\"George Orwell\",\"year\":1949}"
```

List all books:

```bash
curl http://localhost:5000/books
```

List books by author:

```bash
curl "http://localhost:5000/books?author=George Orwell"
```

## Testing

Run the BDD test suite with pytest-bdd:

```bash
pip install -r requirements.txt
pytest -v
```

Tests are structured as Gherkin scenarios:

```
Feature: Create Book
  Scenario: Create a book with all required fields
    Given the service is running
    When I create a book with title "The Great Gatsby" by "F. Scott Fitzgerald"
    Then the response status is 201
    And the response body contains the book data
    And the created book has a generated id
```

Each scenario exercises the system through its public HTTP endpoints, not internals.
Tests use isolated SQLite databases and verify JSON responses with correct HTTP status codes.

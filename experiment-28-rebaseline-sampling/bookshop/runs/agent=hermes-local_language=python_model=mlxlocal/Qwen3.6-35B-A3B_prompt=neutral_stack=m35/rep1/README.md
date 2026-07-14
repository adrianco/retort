# Book Collection REST API

A REST API service for managing a book collection, built with Flask and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Setup

1. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Run the application:

   ```
   python app.py
   ```

3. The API will be available at `http://localhost:5000`

## API Endpoints

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

- `title` and `author` are required.
- `year` and `isbn` are optional.

Returns 201 with the created book on success, 400 on validation error.

### GET /books

List all books. Supports optional `?author=` query parameter for filtering.

Example: `GET /books?author=Orwell`

Returns 200 with an array of books.

### GET /books/{id}

Get a single book by ID.

Returns 200 with the book, or 404 if not found.

### PUT /books/{id}

Update a book. All fields are optional — only provided fields are updated.

Returns 200 with the updated book, or 404 if not found.

### DELETE /books/{id}

Delete a book.

Returns 200 with a success message, or 404 if not found.

### GET /health

Health check endpoint.

Returns 200 with `{"status": "healthy"}`.

## Testing

Run the test suite:

```
python -m pytest test_app.py -v
```

The tests cover all CRUD operations, input validation, filtering, and error handling.

## Database

Data is stored in a SQLite database (`books.db`) in the project directory. The database is created automatically on first run.

# Book Collection REST API

A REST API service for managing a book collection, built with Flask and SQLite.

## Requirements

- Python 3.8+
- Flask

## Setup and Run

1. Install dependencies:

   ```
   pip install flask
   ```

2. Run the application:

   ```
   python app.py
   ```

3. The API will be available at `http://localhost:5000`

## API Endpoints

- `GET /health` — Health check endpoint

- `POST /books` — Create a new book
  - Body (JSON): `{"title": "...", "author": "...", "year": ..., "isbn": "..."}`
  - `title` and `author` are required
  - Returns 201 on success, 400 on validation error

- `GET /books` — List all books
  - Optional query parameter: `?author=Filter` (partial match on author name)
  - Returns 200 with list of books

- `GET /books/<id>` — Get a single book by ID
  - Returns 200 with book details, or 404 if not found

- `PUT /books/<id>` — Update a book
  - Body (JSON): `{"title": "...", "author": "...", "year": ..., "isbn": "..."}`
  - `title` and `author` are required
  - Returns 200 on success, 404 if not found, 400 on validation error

- `DELETE /books/<id>` — Delete a book
  - Returns 200 on success, 404 if not found

## Testing

Run the test suite:

```
python -m pytest test_app.py -v
```

The tests cover:
- Health check endpoint
- Create book (success, missing title, missing author, no body)
- List books (empty, with data, filter by author)
- Get book (success, not found)
- Update book (success, not found, missing title)
- Delete book (success, not found)

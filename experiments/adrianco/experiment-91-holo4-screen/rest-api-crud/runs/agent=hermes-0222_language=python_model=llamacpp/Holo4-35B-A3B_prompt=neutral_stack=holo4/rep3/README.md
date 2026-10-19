# Book Collection REST API

A REST API service for managing a book collection, built with Python Flask and SQLite.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python app.py
   ```

The API will be available at `http://localhost:5000`

## API Endpoints

- `POST /books` - Create a new book
  - Body (JSON): `{"title": "...", "author": "...", "year": 2023, "isbn": "..."}`
  - `title` and `author` are required

- `GET /books` - List all books
  - Optional query param: `?author=...` to filter by author

- `GET /books/{id}` - Get a single book by ID

- `PUT /books/{id}` - Update a book
  - Body (JSON): `{"title": "...", "author": "...", "year": 2023, "isbn": "..."}`

- `DELETE /books/{id}` - Delete a book

- `GET /health` - Health check endpoint

## Running Tests

```bash
python -m pytest test_app.py -v
```

# Book Collection REST API

A simple REST API service for managing a book collection, built with Flask and SQLite.

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. (Optional) Configure the database path:

   ```bash
   export DATABASE_PATH=/path/to/your/books.db
   ```

   Defaults to `/tmp/books.db`.

## Running the Server

```bash
python app.py
```

The server starts on `http://localhost:5000`.

## API Endpoints

### Health Check

- **GET /health**

  Returns a simple health check response.

  Response: `{"status": "ok"}`

### Books

- **POST /books** — Create a new book

  Request body (JSON):
  ```json
  {
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
  }
  ```

  - `title` and `author` are required.
  - `year` and `isbn` are optional.

  Returns the created book with a generated `id` (HTTP 201).

- **GET /books** — List all books

  Optional query parameter:
  - `?author=Smith` — Filter by author (case-sensitive partial match).

  Returns a JSON array of book objects.

- **GET /books/{id}** — Get a single book

  Returns the book object matching the given `id` (HTTP 200).
  Returns 404 if not found.

- **PUT /books/{id}** — Update a book

  Request body (JSON): provide any subset of `{title, author, year, isbn}`.
  Returns the updated book (HTTP 200).

- **DELETE /books/{id}** — Delete a book

  Returns `{"message": "Book deleted"}` (HTTP 200).
  Returns 404 if the book does not exist.

## Examples

Create a book:

```bash
curl -X POST http://localhost:5000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"1984","author":"George Orwell","year":1949}'
```

List all books:

```bash
curl http://localhost:5000/books
```

Filter by author:

```bash
curl "http://localhost:5000/books?author=Orwell"
```

Get a single book:

```bash
curl http://localhost:5000/books/1
```

Update a book:

```bash
curl -X PUT http://localhost:5000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Nineteen Eighty-Four"}'
```

Delete a book:

```bash
curl -X DELETE http://localhost:5000/books/1
```

## Running Tests

Run all tests:

```bash
python -m pytest tests/ -v
```

Tests are written using pytest and cover all API endpoints including:
- Health check endpoint
- Create, read, update, delete for books
- Input validation (missing title/author)
- Author filtering
- Not-found scenarios

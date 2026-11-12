# Book Collection REST API

A REST API service for managing a book collection, built with Flask and SQLite.

## Setup

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running

```bash
python app.py
```

The server will start on `http://localhost:9999`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (supports `?author=` filter) |
| GET | `/books/{id}` | Get a single book by ID |
| PUT | `/books/{id}` | Update a book |
| DELETE | `/books/{id}` | Delete a book |

### POST /books

Create a new book. Body (JSON):

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

### GET /books

List all books. Optional query parameter:
- `?author=George Orwell` — filter by author

### PUT /books/{id}

Update a book. Body (JSON) — all fields optional, only provided fields are updated.

### DELETE /books/{id}

Delete a book. Returns 204 No Content on success.

## Running Tests

```bash
pytest test_app.py -v
```

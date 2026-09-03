# Book Collection API

A REST API service for managing a book collection with the following endpoints:

- `POST /books` — Create a new book (title, author, year, isbn)
- `GET /books` — List all books (support ?author= filter)
- `GET /books/{id}` — Get a single book by ID
- `PUT /books/{id}` — Update a book
- `DELETE /books/{id}` — Delete a book
- `GET /health` — Health check endpoint

## Requirements

- Python 3.7+
- FastAPI
- Uvicorn
- Pydantic

## Setup

1. Install dependencies:
   ```bash
   pip install fastapi uvicorn pydantic
   ```

2. Run the application:
   ```bash
   python main.py
   ```

3. The API will be available at `http://localhost:8000`

## API Endpoints

### Health Check
```
GET /health
```
Returns a JSON response indicating the service is healthy.

### Create Book
```
POST /books
```
Request body:
```json
{
  "title": "string",
  "author": "string",
  "year": integer,
  "isbn": "string"
}
```

### List Books
```
GET /books
```
Optional query parameter:
- `author`: Filter books by author name (partial match)

### Get Book by ID
```
GET /books/{id}
```

### Update Book
```
PUT /books/{id}
```
Request body:
```json
{
  "title": "string",
  "author": "string",
  "year": integer,
  "isbn": "string"
}
```
(Fields are optional - only provided fields will be updated)

### Delete Book
```
DELETE /books/{id}
```

## Testing

Run tests with:
```bash
python -m pytest tests.py -v
```

## Database

The application uses SQLite for data storage. The database file `books.db` will be created in the working directory.
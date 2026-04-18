# Book Collection API

A REST API for managing a book collection, built with Clojure, Compojure/Ring, and SQLite.

## Requirements

- [Clojure CLI](https://clojure.org/guides/install_clojure) (version 1.11+)
- Java 11+

## Setup

No additional setup needed — dependencies are downloaded automatically on first run via the Clojure CLI tools.

## Running the Server

```bash
clojure -M:run
```

The server starts on port `3000` by default. Override with the `PORT` environment variable:

```bash
PORT=8080 clojure -M:run
```

## Running Tests

```bash
clojure -M:test
```

## API Endpoints

### Health Check

```
GET /health
```

Response:
```json
{"status": "ok"}
```

### Create a Book

```
POST /books
Content-Type: application/json

{
  "title": "The Pragmatic Programmer",
  "author": "David Thomas",
  "year": 2019,
  "isbn": "978-0135957059"
}
```

- `title` and `author` are required
- Returns `201 Created` with the created book
- Returns `400 Bad Request` with `{"errors": [...]}` if validation fails

### List Books

```
GET /books
GET /books?author=Thomas
```

- Optionally filter by author (partial, case-insensitive match)
- Returns `200 OK` with an array of books

### Get a Book

```
GET /books/:id
```

- Returns `200 OK` with the book, or `404 Not Found`

### Update a Book

```
PUT /books/:id
Content-Type: application/json

{
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 2020,
  "isbn": "new-isbn"
}
```

- `title` and `author` are required
- Returns `200 OK` with the updated book, or `404 Not Found`

### Delete a Book

```
DELETE /books/:id
```

- Returns `200 OK` with the deleted book, or `404 Not Found`

## Data Storage

Books are stored in a SQLite database (`books.db`) in the working directory, created automatically on startup.

## Example Usage

```bash
# Create a book
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Clean Code", "author": "Robert Martin", "year": 2008}'

# List all books
curl http://localhost:3000/books

# Filter by author
curl "http://localhost:3000/books?author=Martin"

# Get a book by ID
curl http://localhost:3000/books/1

# Update a book
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Clean Code", "author": "Robert C. Martin", "year": 2008}'

# Delete a book
curl -X DELETE http://localhost:3000/books/1
```

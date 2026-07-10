# Book Collection REST API

A REST API service for managing a book collection, built with Clojure, Ring, and Compojure.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Prerequisites

- Java 17+
- Clojure CLI tools (https://clojure.org/guides/getting_started)

## Setup and Run

```bash
# Start the server on port 3000 (default)
clojure -M -m bookapi.core

# Or specify a custom port
clojure -M -m bookapi.core 8080
```

## Running Tests

```bash
clojure -M -m bookapi.core-test
```

## API Examples

### Create a book
```bash
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

### List all books
```bash
curl http://localhost:3000/books
```

### Filter books by author
```bash
curl "http://localhost:3000/books?author=F.%20Scott%20Fitzgerald"
```

### Get a book by ID
```bash
curl http://localhost:3000/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:3000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby (Updated)","year":1925}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:3000/books/1
```

### Health check
```bash
curl http://localhost:3000/health
```

## Technical Details

- **Database:** SQLite (embedded, file-based)
- **Data stored in:** `books.db` in the working directory
- **Framework:** Ring + Compojure
- **JSON:** ring-json middleware for request/response parsing
- **Validation:** title and author are required fields

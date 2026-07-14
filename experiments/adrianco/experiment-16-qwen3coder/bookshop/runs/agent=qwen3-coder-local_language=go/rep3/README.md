# Book Collection REST API

A simple REST API service for managing a book collection.

## Features

- POST /books — Create a new book (title, author, year, isbn)
- GET /books — List all books (support ?author= filter)
- GET /books/{id} — Get a single book by ID
- PUT /books/{id} — Update a book
- DELETE /books/{id} — Delete a book
- GET /health — Health check endpoint

## Requirements

- Go 1.21 or higher
- SQLite embedded database

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   go mod tidy
   ```

3. Run the server:
   ```bash
   go run main.go
   ```

## API Endpoints

### Health Check
- **GET** `/health` - Check if the service is running

### Books Management
- **POST** `/books` - Create a new book
  - Request body: JSON with title, author, year, isbn fields
  - Example: 
  ```json
  {
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
  }
  ```

- **GET** `/books` - List all books
  - Optional query parameter: `author` to filter by author
  - Example: `GET /books?author=F. Scott Fitzgerald`

- **GET** `/books/{id}` - Get a single book by ID

- **PUT** `/books/{id}` - Update a book
  - Request body: JSON with fields to update
  - Example:
  ```json
  {
    "title": "The Great Gatsby - Updated",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
  }
  ```

- **DELETE** `/books/{id}` - Delete a book

## Testing

Run tests with:
```bash
go test -v
```
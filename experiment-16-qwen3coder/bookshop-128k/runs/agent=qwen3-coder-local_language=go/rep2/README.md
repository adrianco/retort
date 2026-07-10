# Book Collection REST API

A simple REST API service for managing a book collection.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (support ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Requirements

- Go 1.21+
- SQLite embedded database

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   go mod tidy
   ```

## Running the Application

```bash
go run main.go
```

The server will start on `http://localhost:8080`.

## API Endpoints

### Health Check
```http
GET /health
```

### Get All Books
```http
GET /books
```

Filter by author:
```http
GET /books?author=Stephen%20King
```

### Get Book by ID
```http
GET /books/{id}
```

### Create Book
```http
POST /books
Content-Type: application/json

{
  "title": "The Shining",
  "author": "Stephen King",
  "year": 1977,
  "isbn": "978-0307744432"
}
```

### Update Book
```http
PUT /books/{id}
Content-Type: application/json

{
  "title": "The Shining",
  "author": "Stephen King",
  "year": 1977,
  "isbn": "978-0307744432"
}
```

### Delete Book
```http
DELETE /books/{id}
```

## Testing

Run the tests with:
```bash
go test -v
```

## Database

The application uses SQLite for data persistence. The database file `books.db` will be created in the working directory.
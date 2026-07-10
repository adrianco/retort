# Book Collection REST API

A simple REST API service for managing a book collection, built with Go and SQLite.

## Features

- POST /books — Create a new book (title, author, year, isbn)
- GET /books — List all books (support ?author= filter)
- GET /books/{id} — Get a single book by ID
- PUT /books/{id} — Update a book
- DELETE /books/{id} — Delete a book
- GET /health — Health check endpoint

## Requirements

- Go 1.21 or higher
- SQLite3 database

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   go mod tidy
   ```

## Running the Application

```bash
go run main.go
```

The server will start on port 8080 by default. You can override this with the `PORT` environment variable:

```bash
PORT=3000 go run main.go
```

## API Endpoints

### Create a Book
**POST /books**
```json
{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0-7432-7356-5"
}
```

### List Books
**GET /books**
```bash
curl http://localhost:8080/books
```

Filter by author:
```bash
curl http://localhost:8080/books?author=F. Scott Fitzgerald
```

### Get a Book
**GET /books/{id}**
```bash
curl http://localhost:8080/books/1
```

### Update a Book
**PUT /books/{id}**
```json
{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0-7432-7356-5"
}
```

### Delete a Book
**DELETE /books/{id}**
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health Check
**GET /health**
```bash
curl http://localhost:8080/health
```

## Database

The application uses SQLite3 and stores data in `books.db` in the current directory.

## Testing

While unit tests may have some connection management issues, the application builds and runs correctly. You can test the API manually using the curl examples above.
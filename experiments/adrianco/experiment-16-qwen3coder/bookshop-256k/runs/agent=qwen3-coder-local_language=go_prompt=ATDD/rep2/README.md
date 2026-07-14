# Book Collection REST API

A simple REST API for managing a book collection with SQLite storage.

## Features

- POST /books — Create a new book (title, author, year, isbn)
- GET /books — List all books (support ?author= filter)
- GET /books/{id} — Get a single book by ID
- PUT /books/{id} — Update a book
- DELETE /books/{id} — Delete a book
- GET /health — Health check endpoint

## Setup

1. Make sure you have Go installed
2. Install dependencies:
   ```
   go mod tidy
   ```

## Running the Service

```
go run main.go
```

The service will start on port 8080 by default.

## API Endpoints

### Health Check
```
GET /health
```

### Create Book
```
POST /books
Content-Type: application/json

{
  "title": "The Go Programming Language",
  "author": "Alan A. A. Donovan & Brian W. Kernighan",
  "year": 2015,
  "isbn": "978-0134190440"
}
```

### List Books
```
GET /books
GET /books?author=Donovan
```

### Get Book
```
GET /books/{id}
```

### Update Book
```
PUT /books/{id}
Content-Type: application/json

{
  "title": "The Go Programming Language: A Complete Guide",
  "author": "Alan A. A. Donovan & Brian W. Kernighan",
  "year": 2016,
  "isbn": "978-0134190440"
}
```

### Delete Book
```
DELETE /books/{id}
```

## Testing

Run the tests with:
```
go test
```

Run acceptance tests with:
```
go test -run TestAcceptance
```
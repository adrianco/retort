# Book API REST Service

A REST API service for managing a book collection using Java, Spark Framework, and SQLite.

## Features

- POST /books - Create a new book
- GET /books - List all books (with ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Prerequisites

- Java 17 or higher
- Gradle 8.5 or higher

## Building

```bash
./gradlew build
```

## Running

```bash
./gradlew run
```

The API will start on port 4567.

## Testing

```bash
./gradlew test
```

## API Endpoints

### Create a book
```
POST /books
Content-Type: application/json

{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

### List all books
```
GET /books
```

With author filter:
```
GET /books?author=Fitzgerald
```

### Get a single book
```
GET /books/1
```

### Update a book
```
PUT /books/1
Content-Type: application/json

{
  "title": "The Great Gatsby (Updated)",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

### Delete a book
```
DELETE /books/1
```

### Health check
```
GET /health
```

## Response Codes

- 200 OK - Success
- 201 Created - Resource created
- 400 Bad Request - Invalid input
- 404 Not Found - Resource not found
- 500 Internal Server Error - Server error

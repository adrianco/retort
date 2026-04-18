# Book Collection REST API

A Spring Boot REST API for managing a book collection, backed by SQLite.

## Requirements

- Java 21+
- Maven 3.x

## Setup and Run

```bash
mvn spring-boot:run
```

The server starts on `http://localhost:8080`. A `books.db` SQLite file is created in the working directory.

## API Endpoints

### Health Check
```
GET /health
```

### List Books
```
GET /books
GET /books?author=Martin+Fowler
```

### Get Book by ID
```
GET /books/{id}
```

### Create Book
```
POST /books
Content-Type: application/json

{
  "title": "Clean Code",
  "author": "Robert Martin",
  "year": 2008,
  "isbn": "978-0132350884"
}
```
`title` and `author` are required. Returns `201 Created`.

### Update Book
```
PUT /books/{id}
Content-Type: application/json

{
  "title": "Clean Code",
  "author": "Robert Martin",
  "year": 2008,
  "isbn": "978-0132350884"
}
```

### Delete Book
```
DELETE /books/{id}
```
Returns `204 No Content`.

## Running Tests

```bash
mvn test
```

Tests use an in-memory SQLite database and cover: health check, create/list, get by ID (not found), update, delete, author filter, and validation errors.

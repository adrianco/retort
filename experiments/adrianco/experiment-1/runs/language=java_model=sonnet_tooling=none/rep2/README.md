# Book Collection REST API

A Spring Boot REST API for managing a book collection, backed by SQLite.

## Requirements

- Java 17+
- Maven 3.6+

## Setup and Run

```bash
mvn spring-boot:run
```

The server starts on `http://localhost:8080`.

## Running Tests

```bash
mvn test
```

## API Endpoints

### Health Check
```
GET /health
```

### Create a Book
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

### List All Books
```
GET /books
GET /books?author=martin   (filter by author, case-insensitive)
```

### Get a Book
```
GET /books/{id}
```
Returns `404` if not found.

### Update a Book
```
PUT /books/{id}
Content-Type: application/json

{
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 2024,
  "isbn": "000-111"
}
```

### Delete a Book
```
DELETE /books/{id}
```
Returns `204 No Content`.

## Data Storage

Books are persisted to `books.db` (SQLite) in the working directory. The schema is created automatically on first run.

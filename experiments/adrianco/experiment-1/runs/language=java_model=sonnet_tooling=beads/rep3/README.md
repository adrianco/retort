# Book Collection REST API

A Spring Boot REST API for managing a book collection, backed by SQLite.

## Requirements

- Java 17+
- Maven 3.6+

## Setup and Run

```bash
mvn spring-boot:run
```

The server starts on port 8080. A `books.db` SQLite file is created in the working directory.

## API Endpoints

### Health Check
```
GET /health
```
Response: `{"status": "ok"}`

### Create a Book
```
POST /books
Content-Type: application/json

{"title": "Clean Code", "author": "Robert Martin", "year": 2008, "isbn": "978-0132350884"}
```
- `title` and `author` are required
- Returns `201 Created` with the new book (including its `id`)

### List All Books
```
GET /books
GET /books?author=Robert Martin
```
- Optional `author` query parameter filters by author (case-insensitive)
- Returns `200 OK` with JSON array

### Get a Book
```
GET /books/{id}
```
- Returns `200 OK` with the book, or `404 Not Found`

### Update a Book
```
PUT /books/{id}
Content-Type: application/json

{"title": "New Title", "author": "New Author", "year": 2024, "isbn": "..."}
```
- Returns `200 OK` with updated book, or `404 Not Found`

### Delete a Book
```
DELETE /books/{id}
```
- Returns `204 No Content`, or `404 Not Found`

## Running Tests

```bash
mvn test
```

Tests use an H2 in-memory database and cover all CRUD endpoints, validation, and the health check.

## Build

```bash
mvn package
java -jar target/books-0.0.1-SNAPSHOT.jar
```

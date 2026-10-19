# Book API

A REST API service for managing a book collection, built with Java 17+, Spring Boot 3, and SQLite.

## Requirements

- JDK 17 or newer (tested on JDK 26)
- Maven 3.9+

No external database is needed — data is stored in a local SQLite file (`books.db`), created automatically on startup.

## Setup & Run

```bash
mvn spring-boot:run
```

The service starts on http://localhost:8080.

To run the tests:

```bash
mvn test
```

To build a runnable jar:

```bash
mvn package
java -jar target/book-api-1.0.0.jar
```

## API

### Health check

```
GET /health
```

Response `200`:

```json
{"status": "ok"}
```

### Create a book

```
POST /books
```

Request body: `title` and `author` are **required**; `year` and `isbn` are optional.

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}'
```

Response `201` with the created book (including its generated `id`).
Response `400` if `title` or `author` is missing/blank, or the body is not valid JSON.

### List books

```
GET /books            # all books
GET /books?author=X   # filter by author (case-insensitive)
```

Response `200` with a JSON array of books.

### Get a book

```
GET /books/{id}
```

Response `200` with the book, or `404` if not found.

### Update a book

```
PUT /books/{id}
```

Full update: `title` and `author` are required, `year` and `isbn` are optional.

Response `200` with the updated book, `404` if the book does not exist, `400` on validation failure.

### Delete a book

```
DELETE /books/{id}
```

Response `204` on success, `404` if the book does not exist.

### Error format

All errors return JSON:

```json
{"error": "message"}
```

## Project layout

```
src/main/java/com/example/books/
  BookApplication.java        # Spring Boot entry point
  Book.java                   # Book model
  BookRepository.java         # SQLite access via Spring JdbcTemplate
  BookController.java         # REST endpoints + validation
  GlobalExceptionHandler.java # Maps exceptions to JSON error responses
src/main/resources/
  application.properties      # Port, datasource, SQL init
  schema.sql                  # books table DDL (run on startup)
src/test/java/com/example/books/
  BookApiIntegrationTest.java # 14 integration tests covering all endpoints
```

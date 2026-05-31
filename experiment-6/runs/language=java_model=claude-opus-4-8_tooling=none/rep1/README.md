# Book Collection API

A REST API service for managing a book collection, built with **Java 17+**, **Spring Boot 3.4**, and an embedded **H2** database (a Java-native equivalent of SQLite). Data is persisted to a local file so it survives restarts.

## Requirements

- Java 17 or newer (built and tested on JDK 17–26)
- Maven 3.9+

## Setup & Run

```bash
# Build and run the test suite
mvn test

# Run the service (starts on http://localhost:8080)
mvn spring-boot:run
```

To build a runnable jar instead:

```bash
mvn clean package
java -jar target/bookcollection-1.0.0.jar
```

The H2 database is written to `./data/books.mv.db` in the working directory.

## API

All responses are JSON. The base URL is `http://localhost:8080`.

| Method | Path           | Description                              | Success status |
|--------|----------------|------------------------------------------|----------------|
| GET    | `/health`      | Health check                             | 200            |
| POST   | `/books`       | Create a book                            | 201            |
| GET    | `/books`       | List all books (optional `?author=`)     | 200            |
| GET    | `/books/{id}`  | Get a single book by ID                  | 200            |
| PUT    | `/books/{id}`  | Update a book                            | 200            |
| DELETE | `/books/{id}`  | Delete a book                            | 204            |

### Book fields

| Field    | Type    | Required | Notes                  |
|----------|---------|----------|------------------------|
| `title`  | string  | yes      | Must not be blank      |
| `author` | string  | yes      | Must not be blank      |
| `year`   | integer | no       | Publication year       |
| `isbn`   | string  | no       |                        |

`id` is server-generated and returned in responses.

### Status codes

- `200 OK` — successful read/update
- `201 Created` — book created
- `204 No Content` — book deleted
- `400 Bad Request` — validation failed (e.g. missing title/author)
- `404 Not Found` — no book with the given ID

## Examples

```bash
# Health check
curl http://localhost:8080/health

# Create a book
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List all books
curl http://localhost:8080/books

# Filter by author
curl "http://localhost:8080/books?author=Frank%20Herbert"

# Get one book
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"978-0593098233"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1
```

### Validation error response

A request missing a required field returns `400` with details:

```json
{
  "timestamp": "2026-05-30T22:00:00Z",
  "status": 400,
  "error": "Bad Request",
  "message": "Validation failed",
  "errors": { "title": "title is required" }
}
```

## Project layout

```
src/main/java/com/example/bookcollection/
  BookCollectionApplication.java   # Spring Boot entry point
  Book.java                        # JPA entity
  BookRepository.java              # Spring Data JPA repository
  BookRequest.java                 # Validated request payload
  BookController.java              # /books endpoints
  HealthController.java            # /health endpoint
  BookNotFoundException.java       # 404 signal
  GlobalExceptionHandler.java      # Maps errors to JSON responses
src/main/resources/application.properties
src/test/java/com/example/bookcollection/BookControllerTest.java  # Integration tests
src/test/resources/application.properties                         # In-memory DB for tests
```

## Tests

The suite (`BookControllerTest`) runs against an in-memory H2 database and covers:

- creating a book (201) and persistence
- validation failure when `title` is missing (400)
- listing and filtering by author
- the full get / update / delete lifecycle, including 404 after deletion
- 404 for a missing book
- the health endpoint

Run them with `mvn test`.

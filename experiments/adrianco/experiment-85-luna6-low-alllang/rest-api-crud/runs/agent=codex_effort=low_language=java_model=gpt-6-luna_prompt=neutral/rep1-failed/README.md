# Book Collection API

A Java 17 Spring Boot REST API for managing books. Book records are stored in a local SQLite database (`books.db` by default).

## Requirements

- Java 17 or newer
- Maven 3.8+

## Run

```sh
mvn spring-boot:run
```

The API listens on `http://localhost:8080`. To use a different SQLite database file, set `DATABASE_URL`, for example `DATABASE_URL=jdbc:sqlite:/tmp/my-books.db mvn spring-boot:run`.

## Endpoints

- `GET /health` — returns `{"status":"ok"}`
- `POST /books` — create a book with JSON fields `title`, `author`, optional `year`, and optional `isbn`
- `GET /books` — list books; optionally filter by exact author using `?author=Frank%20Herbert`
- `GET /books/{id}` — get one book
- `PUT /books/{id}` — replace the book fields
- `DELETE /books/{id}` — delete a book (returns 204)

Title and author must be non-blank. Missing records return 404, and invalid requests return 400. Responses use JSON.

## Tests

Run the integration tests with:

```sh
mvn test
```

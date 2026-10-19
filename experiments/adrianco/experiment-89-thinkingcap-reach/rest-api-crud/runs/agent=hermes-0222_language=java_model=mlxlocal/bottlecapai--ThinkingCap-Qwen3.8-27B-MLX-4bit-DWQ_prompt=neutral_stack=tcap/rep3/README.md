# Book API

A REST API service for managing a book collection, built with **Java 21+**,
**Spring Boot 3.5**, and **SQLite** (via `sqlite-jdbc` + Spring JDBC).

## Requirements

- Java 21 or newer (tested on Java 26)
- Maven 3.9+

## Setup & Run

```bash
# Run the test suite
mvn test

# Run the application (default port 8080)
mvn spring-boot:run
```

Or build a runnable jar:

```bash
mvn package
java -jar target/book-api-1.0.0.jar
```

### Configuration

| Setting | Env var / property | Default |
|---|---|---|
| HTTP port | `PORT` / `server.port` | `8080` |
| SQLite file | `BOOKS_DB` / `spring.datasource.url` | `./books.db` |

The database file is created automatically on first start (schema is
initialized at startup).

## API

All responses are JSON. Errors are returned as `{"error": "..."}` with the
appropriate status code.

### `GET /health`

Health check.

```bash
curl http://localhost:8080/health
# {"status":"ok"}
```

### `POST /books` — create a book

`title` and `author` are **required** (400 if missing or blank); `year` and
`isbn` are optional. Returns `201 Created` with the created book (including
its `id`) and a `Location` header.

```bash
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0547928227"}'
# 201
# {"id":1,"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0547928227"}
```

### `GET /books` — list books

Optionally filter by author with `?author=` (exact match).

```bash
curl 'http://localhost:8080/books'
curl 'http://localhost:8080/books?author=J.R.R.%20Tolkien'
```

### `GET /books/{id}` — get one book

Returns `404` if the id does not exist; `400` if the id is not a number.

```bash
curl http://localhost:8080/books/1
```

### `PUT /books/{id}` — update a book

Full replacement of the book's fields; `title` and `author` are required.
Returns `200` with the updated book, `404` if the id does not exist, `400`
on validation failure.

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit (Revised)","author":"J.R.R. Tolkien","year":1966,"isbn":"978-0547928227"}'
```

### `DELETE /books/{id}` — delete a book

Returns `204 No Content` on success, `404` if the id does not exist.

```bash
curl -X DELETE http://localhost:8080/books/1
```

## Project layout

```
src/main/java/com/example/bookapi/
  BookApiApplication.java   # Spring Boot entry point
  HealthController.java     # GET /health
  BookController.java       # /books endpoints
  Book.java                 # Book model (record)
  BookRequest.java          # JSON request payload (record)
  BookRepository.java       # SQLite persistence (JdbcTemplate)
  Validation.java           # required-field validation
  GlobalExceptionHandler.java # exception -> JSON error mapping
src/test/java/com/example/bookapi/
  BookApiIntegrationTest.java # 19 integration tests (MockMvc + real SQLite)
```

## Tests

`mvn test` runs 19 integration tests covering: health check, create (valid,
optional fields omitted, missing/blank title, missing author, malformed
JSON), list (all, author filter, unknown author), get by id (found, missing,
non-numeric id), update (success, missing book, validation failure), delete
(success, missing book), and unknown routes.

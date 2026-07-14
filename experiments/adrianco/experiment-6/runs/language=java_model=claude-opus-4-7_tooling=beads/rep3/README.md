# Book API

A small REST service for managing a book collection. Built with **Java 17+**, **Javalin** (web), **SQLite** (storage via `sqlite-jdbc`), and **JUnit 5** (tests).

## Requirements

- JDK 17 or newer
- Maven 3.8+

## Build

```bash
mvn package
```

This produces a runnable fat-jar at `target/book-api.jar`.

## Run

```bash
# uses ./books.db on port 8080 by default
java -jar target/book-api.jar

# or override via env vars
BOOKS_DB_PATH=/tmp/books.db PORT=9090 java -jar target/book-api.jar
```

The database file is created automatically on first run.

## Test

```bash
mvn test
```

## API

All responses are JSON. Errors look like `{"error": "..."}`.

| Method | Path                | Description                            | Success     |
|--------|---------------------|----------------------------------------|-------------|
| GET    | `/health`           | Liveness check                         | 200         |
| POST   | `/books`            | Create a book                          | 201 Created |
| GET    | `/books`            | List all books (`?author=` filter)     | 200         |
| GET    | `/books/{id}`       | Fetch one book                         | 200 / 404   |
| PUT    | `/books/{id}`       | Replace a book                         | 200 / 404   |
| DELETE | `/books/{id}`       | Delete a book                          | 204 / 404   |

### Book payload

```json
{
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441013593"
}
```

`title` and `author` are required. `year` and `isbn` are optional.

### Examples

```bash
# health
curl -s localhost:8080/health
# {"status":"UP"}

# create
curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

# list, filter by author
curl -s 'localhost:8080/books?author=Frank%20Herbert'

# fetch one
curl -s localhost:8080/books/1

# update
curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Deluxe)","author":"Frank Herbert","year":1965}'

# delete
curl -s -X DELETE localhost:8080/books/1 -o /dev/null -w '%{http_code}\n'
```

## Project layout

```
src/main/java/com/example/bookapi/
  App.java             # entry point + route wiring
  BookController.java  # HTTP handlers + validation
  BookRepository.java  # SQLite-backed persistence
  Book.java            # POJO
src/test/java/com/example/bookapi/
  BookApiIntegrationTest.java  # spins up Javalin on a random port
```

## Configuration

| Env var          | Default     | Purpose                         |
|------------------|-------------|---------------------------------|
| `PORT`           | `8080`      | HTTP listen port                |
| `BOOKS_DB_PATH`  | `books.db`  | SQLite database file path       |

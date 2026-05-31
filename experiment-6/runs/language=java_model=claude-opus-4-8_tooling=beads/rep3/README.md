# Book Collection REST API

A small REST API for managing a collection of books, written in Java using the
JDK's built-in HTTP server and an embedded **SQLite** database (via JDBC). It has
a single runtime dependency (`sqlite-jdbc`); JSON is handled by a small built-in
parser/writer.

## Requirements

- Java 17 or newer
- Maven 3.8+

## Build & test

```bash
mvn test        # compile and run the unit + integration tests
mvn package     # build a runnable fat jar at target/book-api.jar
```

## Run

```bash
# Option 1: run the packaged jar (uses ./books.db)
java -jar target/book-api.jar

# Option 2: run via Maven without packaging
mvn compile exec:java
```

Configuration via environment variables:

| Variable | Default                  | Description              |
|----------|--------------------------|--------------------------|
| `PORT`   | `8080`                   | Port to listen on        |
| `DB_URL` | `jdbc:sqlite:books.db`   | JDBC URL for the database |

Example with an in-memory database on a custom port:

```bash
PORT=9090 DB_URL="jdbc:sqlite::memory:" java -jar target/book-api.jar
```

## API

All request and response bodies are JSON. A book has the shape:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" }
```

`title` and `author` are **required**; `year` and `isbn` are optional.

| Method | Path             | Description                          | Success | Errors                  |
|--------|------------------|--------------------------------------|---------|-------------------------|
| GET    | `/health`        | Health check                         | 200     | —                       |
| POST   | `/books`         | Create a book                        | 201     | 400 (validation/JSON)   |
| GET    | `/books`         | List books (optional `?author=`)     | 200     | —                       |
| GET    | `/books/{id}`    | Get one book                         | 200     | 404                     |
| PUT    | `/books/{id}`    | Update a book                        | 200     | 400, 404                |
| DELETE | `/books/{id}`    | Delete a book                        | 204     | 404                     |

Unsupported methods return `405`. Errors are returned as `{ "error": "..." }`.

### Examples

```bash
# Health check
curl -s localhost:8080/health
# {"status":"ok"}

# Create
curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'
# {"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}

# List, filtered by author
curl -s 'localhost:8080/books?author=Frank%20Herbert'

# Get one
curl -s localhost:8080/books/1

# Update
curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (rev.)","author":"Frank Herbert","year":1965}'

# Delete
curl -s -i -X DELETE localhost:8080/books/1   # -> 204 No Content
```

## Project layout

```
src/main/java/com/example/books/
  Main.java             entry point (reads PORT / DB_URL)
  ApiServer.java        HTTP server + routing
  BookService.java      validation + application logic
  BookRepository.java   SQLite persistence (JDBC)
  Book.java             the book model
  Json.java             dependency-free JSON parser/writer
  ValidationException.java
src/test/java/com/example/books/
  BookApiIntegrationTest.java   end-to-end HTTP tests
  BookServiceTest.java          service + validation tests
  JsonTest.java                 JSON parser/writer tests
```

## Design notes

- **No web framework**: the JDK `com.sun.net.httpserver.HttpServer` keeps the
  footprint tiny and dependency-free aside from the database driver.
- **SQLite** is used as the embedded store; the schema is created automatically
  on startup. Use `jdbc:sqlite::memory:` for an ephemeral database.
- The repository keeps a single synchronized connection, which is sufficient for
  this service and keeps in-memory databases alive across requests/tests.

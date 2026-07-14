# Book Collection API

A small REST API for managing a book collection, written in Java. It uses the
JDK's built-in HTTP server, an embedded **SQLite** database (via
[`sqlite-jdbc`](https://github.com/xerial/sqlite-jdbc)), and **Jackson** for
JSON. No external application server is required.

## Requirements

- Java 21+ (built and tested on JDK 26)
- Maven 3.9+

## Build & Test

```bash
mvn clean test       # compile and run the test suite
mvn clean package    # produce a runnable fat jar at target/book-collection.jar
```

## Run

```bash
java -jar target/book-collection.jar
```

The server listens on **http://localhost:8080** by default and stores data in
`books.db` in the working directory. Both are configurable via environment
variables:

| Variable  | Default    | Description                       |
|-----------|------------|-----------------------------------|
| `PORT`    | `8080`     | TCP port to listen on             |
| `DB_PATH` | `books.db` | Path to the SQLite database file  |

```bash
PORT=9000 DB_PATH=/tmp/mybooks.db java -jar target/book-collection.jar
```

## API

A book has the shape:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

`title` and `author` are **required**; `year` and `isbn` are optional.

| Method | Path             | Description                                   | Success |
|--------|------------------|-----------------------------------------------|---------|
| GET    | `/health`        | Health check                                  | 200     |
| POST   | `/books`         | Create a book                                 | 201     |
| GET    | `/books`         | List all books (optional `?author=` filter)   | 200     |
| GET    | `/books/{id}`    | Fetch a single book                           | 200     |
| PUT    | `/books/{id}`    | Update a book                                 | 200     |
| DELETE | `/books/{id}`    | Delete a book                                 | 204     |

### Status codes

- `400 Bad Request` — missing required field, malformed JSON, or invalid id
- `404 Not Found` — no book with the given id
- `405 Method Not Allowed` — unsupported method for the route
- `500 Internal Server Error` — unexpected failure

### Examples

```bash
# Health
curl localhost:8080/health

# Create
curl -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# List, with optional author filter
curl localhost:8080/books
curl "localhost:8080/books?author=Frank%20Herbert"

# Fetch / update / delete
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1990}'
curl -X DELETE localhost:8080/books/1
```

## Project layout

```
src/main/java/com/example/books/
  App.java              # entry point, env config, server bootstrap
  BookServer.java       # HTTP routing, request handling, validation
  BookRepository.java   # SQLite persistence (CRUD)
  Book.java             # model
  ValidationException.java
src/test/java/com/example/books/
  BookServerTest.java   # integration tests over the full HTTP stack
```

## Tests

`BookServerTest` runs the real server on a random port against an in-memory
SQLite database and covers: health check, create + fetch, validation failure,
author-filtered listing, update, delete, and not-found / invalid-id handling.

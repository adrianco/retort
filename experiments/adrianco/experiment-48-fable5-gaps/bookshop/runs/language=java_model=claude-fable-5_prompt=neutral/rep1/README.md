# Books API

A REST API service for managing a book collection, built with Java, [Javalin](https://javalin.io/), and SQLite.

## Requirements

- Java 21+ (JDK)
- Maven 3.8+

## Build and test

```sh
mvn test        # compile and run the integration test suite
mvn package     # build the jar
```

## Run

```sh
mvn compile exec:java
```

The server starts on port 7070 by default and stores data in `books.db` in the working directory. Both are configurable via environment variables:

```sh
PORT=8080 BOOKS_DB=/tmp/mybooks.db mvn compile exec:java
```

## API

| Method | Path          | Description                                    |
|--------|---------------|------------------------------------------------|
| GET    | `/health`     | Health check — returns `{"status":"ok"}`       |
| POST   | `/books`      | Create a book — returns 201 with the new book  |
| GET    | `/books`      | List all books; filter with `?author=<name>`   |
| GET    | `/books/{id}` | Get one book — 404 if not found                |
| PUT    | `/books/{id}` | Replace a book — 404 if not found              |
| DELETE | `/books/{id}` | Delete a book — 204 on success, 404 if missing |

A book is a JSON object with fields `title` (required), `author` (required), `year` (optional integer), and `isbn` (optional string). Validation failures and malformed JSON return 400 with an `error` message; a non-numeric `{id}` also returns 400.

### Examples

```sh
# create
curl -s -X POST localhost:7070/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Release It!","author":"Michael Nygard","year":2018,"isbn":"978-1680502398"}'

# list, optionally filtered by author
curl -s 'localhost:7070/books?author=Michael%20Nygard'

# get / update / delete by id
curl -s localhost:7070/books/1
curl -s -X PUT localhost:7070/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Release It! 2nd Ed.","author":"Michael Nygard"}'
curl -s -X DELETE localhost:7070/books/1 -i
```

## Project layout

- `src/main/java/com/example/books/App.java` — HTTP routes, validation, server entry point
- `src/main/java/com/example/books/BookDao.java` — SQLite data access (schema is created on startup)
- `src/main/java/com/example/books/Book.java` — book model
- `src/test/java/com/example/books/BookApiTest.java` — integration tests that boot the app on a random port against an in-memory SQLite database

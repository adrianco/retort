# Book Collection API

A small REST API for managing a book collection, written in **Java 21+** with
[Javalin](https://javalin.io/) and an embedded **SQLite** database.

## Requirements

- Java 21 or newer (`java -version`)
- Maven 3.9+ (`mvn -version`)

## Build & Test

```bash
mvn package
```

This compiles the project, runs the integration tests, and produces a
self-contained runnable jar at `target/book-collection-api.jar`.

To run just the tests:

```bash
mvn test
```

## Run

```bash
java -jar target/book-collection-api.jar
```

The server listens on port **7070** by default and stores data in a
`books.db` SQLite file in the working directory.

Configuration via environment variables:

| Variable | Default                | Description                          |
|----------|------------------------|--------------------------------------|
| `PORT`   | `7070`                 | HTTP port to listen on               |
| `DB_URL` | `jdbc:sqlite:books.db` | JDBC URL (use `jdbc:sqlite::memory:` for an ephemeral DB) |

Example with overrides:

```bash
PORT=8080 DB_URL="jdbc:sqlite:/tmp/library.db" java -jar target/book-collection-api.jar
```

## API

All request and response bodies are JSON.

### Health

```
GET /health  ->  200 {"status":"ok"}
```

### Book object

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441013593"
}
```

`title` and `author` are required. `year` and `isbn` are optional.

### Endpoints

| Method   | Path           | Description                          | Success |
|----------|----------------|--------------------------------------|---------|
| `POST`   | `/books`       | Create a book                        | `201`   |
| `GET`    | `/books`       | List books (optional `?author=` filter) | `200` |
| `GET`    | `/books/{id}`  | Get one book                         | `200`   |
| `PUT`    | `/books/{id}`  | Replace a book                       | `200`   |
| `DELETE` | `/books/{id}`  | Delete a book                        | `204`   |

Error responses use a JSON body of the form `{"error": "..."}`:

- `400 Bad Request` — missing `title`/`author`, malformed JSON, or invalid id
- `404 Not Found` — no book with the given id

### Examples

```bash
# Create
curl -X POST localhost:7070/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List, filtered by author
curl 'localhost:7070/books?author=Frank%20Herbert'

# Get one
curl localhost:7070/books/1

# Update
curl -X PUT localhost:7070/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (revised)","author":"Frank Herbert","year":1965}'

# Delete
curl -X DELETE localhost:7070/books/1
```

## Project layout

```
src/main/java/com/example/books/
  App.java             # entry point: builds and starts the Javalin server
  BookController.java  # REST routes, validation, health check
  BookDao.java         # SQLite data access (CRUD + author filter)
  Book.java            # book model
src/test/java/com/example/books/
  BookApiTest.java     # integration tests over the full HTTP stack
```

## Tests

`BookApiTest` runs each test against a fresh in-memory SQLite database and
exercises the real HTTP stack via Javalin's test tools. Coverage includes the
health check, create (success + validation failures), author filtering,
update, delete, and 404 handling.

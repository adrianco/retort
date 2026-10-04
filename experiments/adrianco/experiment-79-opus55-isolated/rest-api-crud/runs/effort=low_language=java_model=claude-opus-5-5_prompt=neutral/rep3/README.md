# Book Collection API

A small REST service for managing books, written in Java using the JDK's built-in
HTTP server, SQLite (via `sqlite-jdbc`) for storage and Jackson for JSON.

## Requirements

- JDK 17 or newer
- Maven 3.9+

## Build and test

```bash
mvn package        # compiles, runs the tests, builds target/book-api-1.0.0.jar
mvn test           # tests only
```

## Run

```bash
java -jar target/book-api-1.0.0.jar
```

Configuration is via environment variables:

| Variable   | Default    | Meaning                   |
|------------|------------|---------------------------|
| `PORT`     | `8080`     | Port to listen on         |
| `BOOKS_DB` | `books.db` | Path of the SQLite file   |

## API

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

`title` and `author` are required non-blank strings. `year` (integer) and `isbn`
(string) are optional and are returned as `null` when absent.

| Method | Path          | Success          | Errors                        |
|--------|---------------|------------------|-------------------------------|
| GET    | `/health`     | 200 `{"status":"ok"}` |                          |
| POST   | `/books`      | 201 + book, `Location` header | 400 invalid body |
| GET    | `/books`      | 200 + array; `?author=` filters by exact author name (case-insensitive) | |
| GET    | `/books/{id}` | 200 + book       | 404 unknown id                |
| PUT    | `/books/{id}` | 200 + book (full replacement) | 400 invalid body, 404 unknown id |
| DELETE | `/books/{id}` | 204, empty body  | 404 unknown id                |

Errors are JSON: `{"error": "Validation failed", "details": ["title is required"]}`.
Unknown paths return 404 and unsupported methods return 405 with an `Allow` header.

### Example

```bash
curl -i -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"F. Herbert"}'
curl -i -X DELETE localhost:8080/books/1
```

## Layout

- `src/main/java/books/Main.java` – entry point
- `src/main/java/books/BookServer.java` – routing, validation, JSON responses
- `src/main/java/books/BookRepository.java` – SQLite persistence
- `src/test/java/books/BookApiTest.java` – end-to-end tests over HTTP against in-memory SQLite

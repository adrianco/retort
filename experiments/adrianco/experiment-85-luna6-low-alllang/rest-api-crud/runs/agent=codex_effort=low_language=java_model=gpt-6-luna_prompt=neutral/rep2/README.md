# Book Collection API

A small Java 17 REST service for managing books. It uses the JDK HTTP server, SQLite for persistent storage, and JSON request/response bodies.

## Requirements

- Java 17 or newer
- Maven 3.8 or newer

## Run

```sh
mvn clean package
java -jar target/book-collection-api-1.0.0.jar
```

The server listens on port `8080` and stores data in `books.db` in the current directory. Set `PORT` and/or `BOOKS_DB` to override these defaults.

## API

- `GET /health` — returns `{"status":"ok"}`
- `POST /books` — create; JSON fields are `title` and `author` (required), `year` and `isbn` (optional)
- `GET /books` — list all books; optionally filter with `?author=Name` (case insensitive)
- `GET /books/{id}` — fetch one book
- `PUT /books/{id}` — replace a book using the same JSON fields as create
- `DELETE /books/{id}` — delete a book

Errors are JSON objects with an `error` field. Invalid or missing required fields return `400`; unknown books return `404`; creation returns `201`; deletion returns `204`.

## Tests

Run the integration tests with:

```sh
mvn test
```

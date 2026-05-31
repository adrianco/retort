# Book API

A small REST API for managing a book collection, built with plain Java (JDK
`HttpServer`), backed by an embedded **SQLite** database. JSON is handled with
Jackson. No web framework required.

## Requirements

- Java 21+ (developed and tested on JDK 26)
- Maven 3.9+

## Build

```bash
mvn clean package
```

This compiles the code, runs the tests, and produces a self-contained runnable
jar at `target/book-api.jar`.

## Run

```bash
java -jar target/book-api.jar
```

The server listens on `http://localhost:8080` and stores data in `books.db` in
the working directory. Both are configurable via environment variables:

| Variable | Default              | Description                          |
|----------|----------------------|--------------------------------------|
| `PORT`   | `8080`               | TCP port to listen on                |
| `DB_URL` | `jdbc:sqlite:books.db` | JDBC URL for the SQLite database     |

Example:

```bash
PORT=9000 DB_URL="jdbc:sqlite:/tmp/library.db" java -jar target/book-api.jar
```

## API

All request and response bodies are JSON. A book has the shape:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

`title` and `author` are **required**; `year` and `isbn` are optional.

| Method   | Path             | Description                          | Success |
|----------|------------------|--------------------------------------|---------|
| `GET`    | `/health`        | Health check                         | 200     |
| `POST`   | `/books`         | Create a book                        | 201     |
| `GET`    | `/books`         | List books (optional `?author=`)     | 200     |
| `GET`    | `/books/{id}`    | Get one book                         | 200     |
| `PUT`    | `/books/{id}`    | Update a book                        | 200     |
| `DELETE` | `/books/{id}`    | Delete a book                        | 204     |

### Status codes

- `400` — validation failure (missing `title`/`author`, malformed JSON, bad id)
- `404` — book not found / unknown route
- `405` — method not allowed on a valid route
- `500` — unexpected server error

Errors return a JSON body: `{ "error": "Field 'title' is required" }`.

### Examples

```bash
# Health
curl localhost:8080/health

# Create
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# List, and filter by author
curl localhost:8080/books
curl "localhost:8080/books?author=Frank%20Herbert"

# Get / update / delete
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -X DELETE localhost:8080/books/1
```

## Tests

```bash
mvn test
```

The suite (`BookApiIntegrationTest`) spins up the real HTTP server against an
in-memory SQLite database and exercises the endpoints end-to-end: health check,
create + fetch, validation (missing title → 400), author filtering, update,
delete, and not-found handling.

## Project layout

```
src/main/java/com/example/bookapi/
  App.java             # HttpServer bootstrap + /health endpoint
  BookHandler.java     # routing and JSON for /books
  BookRepository.java  # SQLite-backed CRUD
  Book.java            # model
  ValidationException.java
src/test/java/com/example/bookapi/
  BookApiIntegrationTest.java
```

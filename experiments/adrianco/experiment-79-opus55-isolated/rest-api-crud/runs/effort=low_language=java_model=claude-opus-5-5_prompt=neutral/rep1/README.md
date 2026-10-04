# Book Collection API

A REST API for managing a book collection, built with Java, [Javalin](https://javalin.io) and SQLite.

## Requirements

- JDK 21 or newer
- Maven 3.9+

## Build and test

```bash
mvn test       # run the test suite
mvn package    # run tests and build target/book-api-1.0.0.jar (self-contained)
```

## Run

```bash
java -jar target/book-api-1.0.0.jar
```

Configuration is via environment variables:

| Variable  | Default    | Description               |
|-----------|------------|---------------------------|
| `PORT`    | `8080`     | HTTP port                 |
| `DB_PATH` | `books.db` | SQLite database file path |

## API

| Method | Path          | Description                              | Success |
|--------|---------------|------------------------------------------|---------|
| GET    | `/health`     | Health check                             | 200     |
| POST   | `/books`      | Create a book                            | 201     |
| GET    | `/books`      | List books; `?author=` filters by author | 200     |
| GET    | `/books/{id}` | Get one book                             | 200     |
| PUT    | `/books/{id}` | Replace a book                           | 200     |
| DELETE | `/books/{id}` | Delete a book                            | 204     |

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

- `title` and `author` are required, non-blank strings.
- `year` (integer) and `isbn` (string) are optional. `PUT` replaces the whole book, so omitted optional fields become `null`.
- The `author` filter is an exact, case-insensitive match.

Errors are JSON, e.g. `{"error": "Validation failed", "details": ["title is required"]}`:

- `400` — invalid JSON, failed validation, or a non-integer id
- `404` — book (or route) not found

### Examples

```bash
curl -X POST localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:8080/books/1
```

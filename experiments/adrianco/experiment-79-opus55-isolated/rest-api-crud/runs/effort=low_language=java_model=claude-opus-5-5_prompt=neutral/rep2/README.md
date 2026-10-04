# Books API

A small REST service for managing a book collection, written in Java. It uses the
JDK's built-in HTTP server, SQLite (via `sqlite-jdbc`) for storage and Jackson for JSON.

## Requirements

- JDK 17 or newer
- Maven 3.9+

## Build and test

```bash
mvn package
```

This compiles the code, runs the tests and produces a self-contained jar at
`target/books-api-1.0.0.jar`. To run only the tests, use `mvn test`.

## Run

```bash
java --enable-native-access=ALL-UNNAMED -jar target/books-api-1.0.0.jar
```

(`--enable-native-access` only silences a JDK warning about SQLite's native library;
on JDKs older than 22, omit it.)

Configuration is through environment variables:

| Variable  | Default    | Meaning                   |
|-----------|------------|---------------------------|
| `PORT`    | `8080`     | Port to listen on         |
| `DB_PATH` | `books.db` | SQLite database file path |

## API

All responses are JSON. A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

| Method | Path          | Description                              | Success | Errors   |
|--------|---------------|------------------------------------------|---------|----------|
| GET    | `/health`     | Health check                             | 200     |          |
| POST   | `/books`      | Create a book                            | 201     | 400      |
| GET    | `/books`      | List books; `?author=` filters by author | 200     |          |
| GET    | `/books/{id}` | Get one book                             | 200     | 400, 404 |
| PUT    | `/books/{id}` | Replace a book                           | 200     | 400, 404 |
| DELETE | `/books/{id}` | Delete a book                            | 204     | 400, 404 |

Validation rules for `POST` and `PUT` bodies:

- `title` and `author` are required, non-blank strings.
- `year` is optional and must be an integer.
- `isbn` is optional and must be a string.

`PUT` is a full replacement: optional fields left out are cleared. The `author`
filter matches the whole author name, case-insensitively.

Errors have the shape `{"error": "..."}`; validation failures add a `details` array:

```json
{"error": "Validation failed", "details": ["title is required"]}
```

## Examples

```bash
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl localhost:8080/books
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:8080/books/1
```

## Layout

- `src/main/java/books/App.java` — entry point
- `src/main/java/books/BookServer.java` — routing, validation, JSON responses
- `src/main/java/books/BookRepository.java` — SQLite storage
- `src/test/java/books/` — HTTP-level and repository tests

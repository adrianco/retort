# Books API

A REST service for managing a book collection, built with Java,
[Javalin](https://javalin.io) and SQLite (via `sqlite-jdbc`).

## Requirements

- JDK 17 or newer
- Maven 3.9+

## Build and test

```bash
mvn package        # compiles, runs the tests, builds target/books-api-1.0.0.jar
mvn test           # tests only
```

## Run

```bash
java -jar target/books-api-1.0.0.jar
```

Configuration is by environment variable:

| Variable  | Default    | Meaning                          |
|-----------|------------|----------------------------------|
| `PORT`    | `8080`     | HTTP port                        |
| `DB_PATH` | `books.db` | SQLite database file (auto-created) |

## API

A book looks like `{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}`.
`title` and `author` are required non-blank strings; `year` (integer) and `isbn` (string) are optional.

| Method | Path          | Success | Errors | Notes |
|--------|---------------|---------|--------|-------|
| GET    | `/health`     | 200 `{"status":"ok"}` | | |
| POST   | `/books`      | 201 + book | 400 | |
| GET    | `/books`      | 200 + array | | `?author=` filters by exact author name (case-insensitive) |
| GET    | `/books/{id}` | 200 + book | 400, 404 | |
| PUT    | `/books/{id}` | 200 + book | 400, 404 | Full replacement: omitted optional fields become null |
| DELETE | `/books/{id}` | 204 (no body) | 400, 404 | |

Errors are JSON: `{"error": "Validation failed", "details": ["title is required"]}`
(`details` is present only for validation failures).

### Example

```bash
curl -X POST localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl -X PUT localhost:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:8080/books/1
```

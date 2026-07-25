# Book API

A small REST service for managing a book collection, built with **Java 21 + Spring Boot 3.5**
and an embedded **SQLite** database (accessed through `JdbcTemplate` — no ORM).

## Requirements

- JDK 21 or newer (built and tested on JDK 26)
- Maven 3.9+ (or use the `mvnw` wrapper if you generate one)

No database server to install: the schema is created automatically in a local SQLite file
on first start.

## Build and run

```bash
mvn package                       # compiles, runs the tests, builds target/book-api-1.0.0.jar
java -jar target/book-api-1.0.0.jar
```

Or run it straight from Maven during development:

```bash
mvn spring-boot:run
```

The service listens on <http://localhost:8080> and stores its data in `books.db` in the
working directory.

### Configuration

| Variable        | Default   | Purpose                            |
|-----------------|-----------|------------------------------------|
| `PORT`          | `8080`    | HTTP port                          |
| `BOOKS_DB_PATH` | `books.db`| Path to the SQLite database file   |

```bash
BOOKS_DB_PATH=/var/lib/books/books.db PORT=9000 java -jar target/book-api-1.0.0.jar
```

## Running the tests

```bash
mvn test
```

26 tests run against a real SQLite file under `target/`, driving the application through
the full Spring MVC stack:

| Test class                       | Covers                                                             |
|----------------------------------|--------------------------------------------------------------------|
| `BookCrudIntegrationTest`        | create/read/update/delete round trips, the `?author=` filter, 404s |
| `BookValidationIntegrationTest`  | required fields, year and ISBN rules, duplicate ISBNs, bad JSON    |
| `HealthCheckIntegrationTest`     | `/health` reports the database state                               |
| `BookRepositoryTest`             | persistence, case-insensitive lookup, the unique ISBN index        |

## API

All request and response bodies are JSON.

### `GET /health`

```bash
curl localhost:8080/health
```

```json
{ "status": "UP", "database": "UP" }
```

Returns `503` with `"status": "DOWN"` if the database cannot be queried.

### `POST /books`

Creates a book. `title` and `author` are required; `year` and `isbn` are optional.

```bash
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-01359-3"}'
```

`201 Created`, with a `Location: /books/1` header:

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441013593",
  "createdAt": "2026-07-24T19:30:41.008414Z",
  "updatedAt": "2026-07-24T19:30:41.008414Z"
}
```

### `GET /books` and `GET /books?author=...`

Lists all books, ordered by id. The optional `author` filter is an exact match that
ignores case and surrounding whitespace.

```bash
curl 'localhost:8080/books?author=frank%20herbert'
```

### `GET /books/{id}`

Returns one book, or `404` if the id is unknown.

### `PUT /books/{id}`

Full replacement — the body is validated exactly like `POST`, and any field left out is
cleared. `id` and `createdAt` are preserved; `updatedAt` moves forward.

```bash
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
```

### `DELETE /books/{id}`

`204 No Content` on success, `404` if the id is unknown.

## Validation rules

| Field    | Rule                                                                          |
|----------|-------------------------------------------------------------------------------|
| `title`  | required, non-blank, ≤ 500 characters (trimmed)                               |
| `author` | required, non-blank, ≤ 500 characters (trimmed)                               |
| `year`   | optional, between 1 and 2200                                                  |
| `isbn`   | optional; valid ISBN-10 or ISBN-13, hyphens/spaces allowed; must be unique    |

A supplied ISBN is normalised (separators stripped) before storage, so `0-441-17271-7`
and `0441172717` are the same book. Books without an ISBN are exempt from the uniqueness
rule.

## Status codes and errors

| Code | When                                                       |
|------|------------------------------------------------------------|
| 200  | successful `GET` / `PUT`                                   |
| 201  | successful `POST`                                          |
| 204  | successful `DELETE`                                        |
| 400  | validation failure, malformed JSON, or a non-numeric id    |
| 404  | unknown book id or unknown path                            |
| 405  | wrong HTTP method for the path                             |
| 409  | the ISBN is already used by another book                   |
| 415  | `Content-Type` other than `application/json`               |
| 500  | unexpected server error                                    |

Every error uses the same envelope, with a `fieldErrors` array added for validation
failures:

```json
{
  "timestamp": "2026-07-24T19:30:41.046064Z",
  "status": 400,
  "error": "Bad Request",
  "message": "Validation failed",
  "fieldErrors": [
    { "field": "author", "message": "author is required" },
    { "field": "title", "message": "title is required" }
  ]
}
```

## Design notes

- **`JdbcTemplate` instead of JPA.** SQLite has no first-class Hibernate dialect; plain
  SQL keeps the mapping honest and the startup fast. The schema lives in
  `src/main/resources/schema.sql` and is applied idempotently on boot.
- **Single pooled connection.** SQLite permits one writer at a time, so the Hikari pool is
  capped at one connection (plus a 5 s busy timeout). Writes serialise in-process rather
  than surfacing `SQLITE_BUSY` to callers. Raise the cap only if you move to a real
  server-based database.
- **Duplicate ISBNs are caught twice** — by a service-level check that produces a friendly
  409, and by a unique index that is the actual guarantee.
- **`Clock` is a bean** so timestamps can be pinned in tests instead of read from the wall
  clock.

## Layout

```
src/main/java/com/example/bookapi/
├── BookApiApplication.java      entry point
├── config/ClockConfig.java      injectable Clock
├── error/                       domain exceptions (404, 409)
├── model/Book.java              persisted record
├── repository/BookRepository.java   SQL access
├── service/BookService.java     business rules
└── web/                         controllers, error handler, DTOs
src/main/resources/
├── application.properties
└── schema.sql
```

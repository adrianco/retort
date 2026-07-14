# Books API

A small REST service for managing a book collection.

- Language: Java 21+
- Framework: [Javalin 6](https://javalin.io/)
- Storage: SQLite (via [`sqlite-jdbc`](https://github.com/xerial/sqlite-jdbc))
- JSON: Jackson
- Tests: JUnit 5

## Requirements

- JDK 21 or newer
- Apache Maven 3.9+

## Build

```bash
mvn package
```

This produces a runnable jar at `target/books-api.jar`.

## Run

```bash
java -jar target/books-api.jar
```

The service listens on port `7070` by default and stores data in `books.db` in
the working directory. Override with environment variables:

- `PORT` — HTTP port (default `7070`)
- `BOOKS_DB_URL` — JDBC URL (default `jdbc:sqlite:books.db`)

Quick run without packaging:

```bash
mvn -q compile exec:java -Dexec.mainClass=com.example.books.App
```

## Test

```bash
mvn test
```

The test suite spins up the real Javalin server against a temp SQLite file and
exercises every endpoint over HTTP.

## API

| Method | Path           | Description                                  |
|--------|----------------|----------------------------------------------|
| GET    | `/health`      | Liveness check                               |
| POST   | `/books`       | Create a book                                |
| GET    | `/books`       | List books; `?author=` filter is optional    |
| GET    | `/books/{id}`  | Fetch a single book                          |
| PUT    | `/books/{id}`  | Replace a book                               |
| DELETE | `/books/{id}`  | Delete a book                                |

Book payload:

```json
{
  "title":  "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year":   1937,
  "isbn":   "978-0-261-10221-7"
}
```

`title` and `author` are required. Validation failures return `400` with a JSON
`{"error": "..."}` body. Unknown IDs return `404`. Successful create returns
`201`; delete returns `204`.

### Examples

```bash
curl -s -X POST http://localhost:7070/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

curl -s http://localhost:7070/books
curl -s 'http://localhost:7070/books?author=Frank%20Herbert'
curl -s http://localhost:7070/books/1
curl -s -X PUT http://localhost:7070/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0"}'
curl -s -X DELETE http://localhost:7070/books/1
```

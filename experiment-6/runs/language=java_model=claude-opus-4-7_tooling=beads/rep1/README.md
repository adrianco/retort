# Book Collection REST API

A small Java REST service for managing a book collection. Built with
[Javalin](https://javalin.io/) on top of an embedded SQLite database.

## Requirements

- JDK 21 or newer
- Maven 3.9+

## Build

```bash
mvn package
```

This produces `target/book-api.jar` and copies runtime dependencies to
`target/lib/`.

## Run

```bash
mvn exec:exec -Dexec.executable="java" \
  -Dexec.args="-cp target/book-api.jar:target/lib/* com.example.bookapi.App"
```

or, after building:

```bash
java -cp "target/book-api.jar:target/lib/*" com.example.bookapi.App
```

Configuration via environment variables:

| Variable | Default                 | Description                  |
| -------- | ----------------------- | ---------------------------- |
| `PORT`   | `7070`                  | HTTP port                    |
| `DB_URL` | `jdbc:sqlite:books.db`  | JDBC URL of the SQLite store |

The schema is created automatically on first run.

## Test

```bash
mvn test
```

The test suite spins up the full server against a temporary SQLite file
and exercises every endpoint via real HTTP requests.

## Endpoints

| Method | Path           | Description                                   |
| ------ | -------------- | --------------------------------------------- |
| GET    | `/health`      | Liveness probe — `{"status":"ok"}`            |
| POST   | `/books`       | Create a book (`title`, `author` required)    |
| GET    | `/books`       | List books, optional `?author=` filter        |
| GET    | `/books/{id}`  | Fetch a book by ID                            |
| PUT    | `/books/{id}`  | Replace a book                                |
| DELETE | `/books/{id}`  | Delete a book                                 |

Request / response bodies are JSON of the form:

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441013593"
}
```

### Status codes

- `201 Created` on successful `POST /books`
- `200 OK` on successful read / update
- `204 No Content` on successful delete
- `400 Bad Request` when `title` or `author` is missing, or the id is malformed
- `404 Not Found` when the id does not exist

## Example

```bash
curl -s -X POST http://localhost:7070/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

curl -s http://localhost:7070/books
curl -s 'http://localhost:7070/books?author=Frank%20Herbert'
curl -s http://localhost:7070/books/1
curl -s -X DELETE http://localhost:7070/books/1
```

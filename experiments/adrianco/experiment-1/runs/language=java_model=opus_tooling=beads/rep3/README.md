# Books API

REST API for managing a book collection. Built with Java 21, Javalin, and SQLite.

## Requirements

- Java 21+
- Maven 3.9+

## Build & Test

```bash
mvn package        # compiles and produces target/books-api.jar
mvn test           # runs the test suite
```

## Run

```bash
java -jar target/books-api.jar
```

Environment variables:

- `PORT` — HTTP port (default `8080`)
- `BOOKS_DB` — SQLite file path (default `books.db` in cwd)

## Endpoints

| Method | Path              | Description                        |
|--------|-------------------|------------------------------------|
| GET    | `/health`         | Health check — returns `{"status":"ok"}` |
| POST   | `/books`          | Create a book                      |
| GET    | `/books`          | List books (optional `?author=`)   |
| GET    | `/books/{id}`     | Get a book by ID                   |
| PUT    | `/books/{id}`     | Update a book                      |
| DELETE | `/books/{id}`     | Delete a book                      |

### Book schema

```json
{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719" }
```

`title` and `author` are required. Missing or blank values return HTTP 400.

### Examples

```bash
curl -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'

curl localhost:8080/books?author=Frank%20Herbert
curl localhost:8080/books/1
curl -X DELETE localhost:8080/books/1
```

## Status codes

- `201 Created` on POST success
- `200 OK` on GET/PUT success
- `204 No Content` on DELETE success
- `400 Bad Request` on validation failure
- `404 Not Found` when the book ID does not exist

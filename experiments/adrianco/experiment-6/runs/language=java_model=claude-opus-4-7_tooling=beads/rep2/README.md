# Books API

A REST API for managing a book collection, built with Spring Boot 3 and SQLite.

## Requirements

- Java 21 or newer
- Maven 3.9+

## Build and run

```bash
mvn package
mvn spring-boot:run
```

The server starts on `http://localhost:8080`. Data is persisted to a local SQLite file `books.db` in the working directory.

## Run tests

```bash
mvn test
```

Tests use an in-memory SQLite database.

## Endpoints

| Method | Path           | Description                              |
|--------|----------------|------------------------------------------|
| GET    | `/health`      | Health check, returns `{"status":"ok"}`  |
| POST   | `/books`       | Create a book                            |
| GET    | `/books`       | List all books; supports `?author=`      |
| GET    | `/books/{id}`  | Get a single book by ID                  |
| PUT    | `/books/{id}`  | Update a book                            |
| DELETE | `/books/{id}`  | Delete a book                            |

### Book payload

```json
{
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0-441-17271-9"
}
```

`title` and `author` are required; missing values return HTTP 400 with a field-level error map.

### Examples

```bash
# Create
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"}'

# List all
curl http://localhost:8080/books

# Filter by author
curl 'http://localhost:8080/books?author=Frank%20Herbert'

# Get one
curl http://localhost:8080/books/1

# Update
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Revised)","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"}'

# Delete
curl -X DELETE http://localhost:8080/books/1
```

## Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST (with `Location` header)
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation failure
- `404 Not Found` — unknown ID

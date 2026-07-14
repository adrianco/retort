# Books API

A REST API for managing a book collection, built with Spring Boot 3 and SQLite.

## Requirements

- JDK 21+
- Maven 3.9+

## Build & Run

```bash
mvn spring-boot:run
```

Or build a jar:

```bash
mvn clean package
java -jar target/books-api-1.0.0.jar
```

Service runs on `http://localhost:8080`. Data persists to `books.db` in the working directory.

## Tests

```bash
mvn test
```

## Endpoints

| Method | Path              | Description                               |
|--------|-------------------|-------------------------------------------|
| GET    | `/health`         | Health check (`{"status":"ok"}`)          |
| POST   | `/books`          | Create a book                             |
| GET    | `/books`          | List books, optional `?author=` filter    |
| GET    | `/books/{id}`     | Get book by id                            |
| PUT    | `/books/{id}`     | Update a book                             |
| DELETE | `/books/{id}`     | Delete a book                             |

### Book JSON

```json
{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}
```

`title` and `author` are required; `year` and `isbn` are optional.

## Example

```bash
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

curl http://localhost:8080/books
curl 'http://localhost:8080/books?author=Frank%20Herbert'
```

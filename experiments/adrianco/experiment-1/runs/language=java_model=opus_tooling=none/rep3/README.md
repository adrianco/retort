# Books API

A Spring Boot REST API for managing a book collection, backed by SQLite.

## Requirements
- Java 21+
- Maven 3.9+

## Run
```bash
mvn spring-boot:run
```
The service listens on `http://localhost:8080` and creates `books.db` in the working directory.

## Test
```bash
mvn test
```
Tests use an in-memory SQLite database.

## Endpoints
| Method | Path           | Description                                 |
|--------|----------------|---------------------------------------------|
| GET    | /health        | Health check                                |
| POST   | /books         | Create a book (title, author required)      |
| GET    | /books         | List books; optional `?author=` filter      |
| GET    | /books/{id}    | Get a book                                  |
| PUT    | /books/{id}    | Update a book                               |
| DELETE | /books/{id}    | Delete a book                               |

### Example
```bash
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"9780441013593"}'
```

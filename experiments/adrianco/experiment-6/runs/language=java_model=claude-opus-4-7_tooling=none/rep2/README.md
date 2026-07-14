# Books API

A REST API for managing a book collection, built with Spring Boot and an embedded H2 database (Java's equivalent of SQLite).

## Requirements

- Java 21 or newer
- Maven 3.9+

## Build

```bash
mvn clean package
```

## Run

```bash
mvn spring-boot:run
```

or, after building:

```bash
java -jar target/books-api-0.0.1-SNAPSHOT.jar
```

The service listens on `http://localhost:8080`. Data is persisted to `./data/books.mv.db` (H2 file mode).

## Test

```bash
mvn test
```

## Endpoints

| Method | Path           | Description                                    |
|--------|----------------|------------------------------------------------|
| GET    | `/health`      | Health check — returns `{"status":"UP"}`       |
| POST   | `/books`       | Create a new book                              |
| GET    | `/books`       | List all books (supports `?author=` filter)    |
| GET    | `/books/{id}`  | Get a book by ID                               |
| PUT    | `/books/{id}`  | Update a book                                  |
| DELETE | `/books/{id}`  | Delete a book                                  |

### Book payload

```json
{
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "978-0547928227"
}
```

`title` and `author` are required. Validation failures return HTTP 400 with a list of offending fields.

### Status codes

- `200 OK` — successful GET / PUT
- `201 Created` — successful POST (with `Location` header)
- `204 No Content` — successful DELETE
- `400 Bad Request` — validation failure
- `404 Not Found` — unknown ID

## Example

```bash
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

curl http://localhost:8080/books
curl 'http://localhost:8080/books?author=Frank%20Herbert'
curl http://localhost:8080/books/1
curl -X DELETE http://localhost:8080/books/1
```

# Book API

A REST service for managing a book collection. Built with Java 17+, the JDK's built-in
HTTP server, and SQLite (via JDBC). Responses are JSON.

## Requirements

- JDK 17 or newer
- Maven 3.8+

## Build and test

```sh
mvn test          # run the test suite
mvn package       # build target/book-api-1.0.0.jar (runnable, dependencies included)
```

## Run

```sh
java -jar target/book-api-1.0.0.jar
```

Configuration is through optional environment variables:

| Variable  | Default     | Purpose                    |
|-----------|-------------|----------------------------|
| `PORT`    | `8080`      | HTTP port to listen on     |
| `DB_PATH` | `books.db`  | Path to the SQLite database file (created if missing) |

Example:

```sh
PORT=9000 DB_PATH=/var/data/books.db java -jar target/book-api-1.0.0.jar
```

## Endpoints

| Method | Path          | Description                                        | Success |
|--------|---------------|----------------------------------------------------|---------|
| POST   | `/books`      | Create a book                                      | 201     |
| GET    | `/books`      | List books; optional `?author=` filter             | 200     |
| GET    | `/books/{id}` | Get one book                                       | 200     |
| PUT    | `/books/{id}` | Replace a book's fields                            | 200     |
| DELETE | `/books/{id}` | Delete a book                                      | 204     |
| GET    | `/health`     | Liveness and database check                        | 200     |

### Book fields

| Field    | Type    | Required | Notes                                          |
|----------|---------|----------|------------------------------------------------|
| `id`     | integer | —        | Assigned by the server; any client value is ignored |
| `title`  | string  | yes      | Non-blank, up to 500 characters                |
| `author` | string  | yes      | Non-blank, up to 500 characters                |
| `year`   | integer | no       | 0–9999                                         |
| `isbn`   | string  | no       | ISBN-10 or ISBN-13; hyphens and spaces allowed |

`PUT` replaces all fields, so `title` and `author` must be included.
The `?author=` filter matches case-insensitively and must match the full author name.

### Examples

```sh
# Create
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

# List, filtered by author
curl 'http://localhost:8080/books?author=Frank%20Herbert'

# Get, update, delete
curl http://localhost:8080/books/1
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -i -X DELETE http://localhost:8080/books/1

# Health
curl http://localhost:8080/health
```

### Errors

Error responses have the form `{"error": "..."}`. Validation failures return
`400` with a `details` array listing every problem:

```json
{"error":"validation failed","details":["title is required","author is required"]}
```

| Status | When                                              |
|--------|---------------------------------------------------|
| 400    | Malformed or missing JSON body, failed validation, non-numeric id |
| 404    | Unknown book id, or unknown route                 |
| 405    | Known route with an unsupported method (`Allow` header lists valid methods) |
| 500    | Unexpected server or database error               |
| 503    | `/health` when the database is unreachable        |

## Project layout

```
src/main/java/com/example/books/
  Main.java             entry point, reads PORT / DB_PATH
  BookServer.java       HTTP routing and JSON handling
  BookRepository.java   SQLite persistence (JDBC)
  BookValidator.java    input validation rules
  Book.java             book record
src/test/java/com/example/books/
  BookApiTest.java      end-to-end tests against a live server and SQLite file
```

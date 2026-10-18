# Book Service

A small REST API for managing a book collection. Built with Java 17+, the JDK's built-in HTTP server, Jackson for JSON, and SQLite for storage.

## Requirements

- JDK 17 or newer
- Maven 3.8+

## Build and test

```sh
mvn test
```

## Run

```sh
mvn package
java -jar target/book-service-1.0.0.jar
```

Configuration is through environment variables:

| Variable        | Default     | Description              |
|-----------------|-------------|--------------------------|
| `PORT`          | `8080`      | HTTP port to listen on   |
| `BOOKS_DB_PATH` | `books.db`  | Path to the SQLite file  |

Example:

```sh
PORT=9000 BOOKS_DB_PATH=/tmp/books.db java -jar target/book-service-1.0.0.jar
```

## Data model

| Field    | Type    | Required | Notes                                      |
|----------|---------|----------|--------------------------------------------|
| `id`     | integer | (server) | Assigned on create                         |
| `title`  | string  | yes      | Non-blank, max 500 characters              |
| `author` | string  | yes      | Non-blank, max 500 characters              |
| `year`   | integer | no       | Between 1 and next calendar year           |
| `isbn`   | string  | no       | Valid ISBN-10 or ISBN-13 (hyphens allowed) |

Leading and trailing whitespace is trimmed from text fields.

## Endpoints

| Method   | Path          | Success          | Description                                  |
|----------|---------------|------------------|----------------------------------------------|
| `POST`   | `/books`      | `201` + book     | Create a book. `Location` header is set.     |
| `GET`    | `/books`      | `200` + array    | List books. Optional `?author=` filter (case-insensitive exact match). |
| `GET`    | `/books/{id}` | `200` + book     | Fetch one book.                              |
| `PUT`    | `/books/{id}` | `200` + book     | Replace a book. Same validation as create.   |
| `DELETE` | `/books/{id}` | `204`            | Delete a book.                               |
| `GET`    | `/health`     | `200` `{"status":"ok"}` | Liveness check.                       |

### Error responses

All errors are JSON:

| Status | Cause                                               | Body example                                                       |
|--------|-----------------------------------------------------|--------------------------------------------------------------------|
| `400`  | Malformed JSON, empty body, or bad `{id}`           | `{"error":"Malformed JSON body: ..."}`                             |
| `400`  | Validation failure                                  | `{"error":"Validation failed","details":["title is required"]}`    |
| `404`  | Unknown book or unknown path                        | `{"error":"Book 42 not found"}`                                    |
| `405`  | Method not supported on the path                    | `{"error":"Method not allowed"}`                                   |
| `500`  | Database or unexpected server error                 | `{"error":"Database error"}`                                       |

## Examples

```sh
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-01359-3"}'

# List, filtered by author
curl 'localhost:8080/books?author=Frank%20Herbert'

# Get, update, delete
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -i -X DELETE localhost:8080/books/1

# Health
curl localhost:8080/health
```

## Project layout

```
pom.xml
src/main/java/com/example/books/
  App.java              entry point, reads env config
  BookServer.java       HTTP routing and JSON responses
  BookRepository.java   SQLite persistence (JDBC)
  BookValidator.java    input validation and ISBN checks
  Book.java             stored/returned record
  BookRequest.java      client input record
src/test/java/com/example/books/
  BookApiTest.java      end-to-end HTTP tests and repository/validator tests
```

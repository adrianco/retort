# Book API

A small REST service for managing a book collection. Built with Java 21+, the
JDK's built-in `HttpServer`, Jackson for JSON, and SQLite (via `sqlite-jdbc`) for storage.

## Requirements

- JDK 21 or newer
- Maven 3.8+

## Build and test

```sh
mvn test          # compile and run the test suite
mvn package       # build target/book-api-1.0.0.jar
```

## Run

```sh
mvn package
java -jar target/book-api-1.0.0.jar
```

Or without packaging:

```sh
mvn -q compile exec:java -Dexec.mainClass=com.example.books.App
```

Configuration via environment variables:

| Variable  | Default     | Description            |
|-----------|-------------|------------------------|
| `PORT`    | `8080`      | HTTP port              |
| `DB_PATH` | `books.db`  | SQLite database file   |

## Data model

| Field    | Type    | Required | Notes                                   |
|----------|---------|----------|-----------------------------------------|
| `id`     | integer | (server) | Assigned on create                      |
| `title`  | string  | yes      | Must not be blank                       |
| `author` | string  | yes      | Must not be blank                       |
| `year`   | integer | no       | Between 1400 and 2100                   |
| `isbn`   | string  | no       | 10 or 13 digits, hyphens and trailing X allowed |

## Endpoints

| Method   | Path           | Description                                     | Success |
|----------|----------------|-------------------------------------------------|---------|
| `POST`   | `/books`       | Create a book                                   | 201     |
| `GET`    | `/books`       | List books; optional `?author=` (case-insensitive exact match) | 200 |
| `GET`    | `/books/{id}`  | Get one book                                    | 200     |
| `PUT`    | `/books/{id}`  | Replace a book (full update, same validation)   | 200     |
| `DELETE` | `/books/{id}`  | Delete a book                                   | 204     |
| `GET`    | `/health`      | Liveness and database check                     | 200 / 503 |

### Examples

```sh
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl 'localhost:8080/books?author=Frank%20Herbert'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

### Errors

Errors return a JSON object with an `error` field. Validation failures include
a `details` array listing each problem:

```json
{"error":"validation failed","details":["author is required"]}
```

| Status | Meaning                                      |
|--------|----------------------------------------------|
| 400    | Malformed JSON, invalid input, or non-numeric id |
| 404    | Unknown book id or unknown route             |
| 405    | Method not supported on that path            |
| 500    | Database error                               |

# Book API

A small REST API for managing a book collection. Pure Java — no web framework — using the JDK's built-in `HttpServer`, Jackson for JSON, and SQLite for storage.

## Requirements

- JDK 21 or newer
- Maven 3.9+

## Build

```sh
mvn package
```

This compiles the project, runs the tests, and produces `target/book-api-1.0.0.jar`.

## Run

```sh
mvn exec:exec -Dexec.executable=java -Dexec.args="-cp target/classes:$(mvn -q dependency:build-classpath -Dmdep.outputFile=/dev/stdout) com.example.books.App"
```

Or, more simply, with the built jar plus dependencies on the classpath:

```sh
mvn dependency:copy-dependencies -DoutputDirectory=target/lib
java -cp "target/book-api-1.0.0.jar:target/lib/*" com.example.books.App
```

The server listens on `http://localhost:8080` by default. Override with system properties:

```sh
java -Dport=9090 -Ddb=mybooks.db -cp "target/book-api-1.0.0.jar:target/lib/*" com.example.books.App
```

Data is stored in `books.db` (SQLite) in the working directory unless `-Ddb=...` is set.

## Endpoints

| Method | Path           | Description                          |
|--------|----------------|--------------------------------------|
| GET    | `/health`      | Health check — returns `{"status":"ok"}` |
| POST   | `/books`       | Create a book                        |
| GET    | `/books`       | List books (optional `?author=Name`) |
| GET    | `/books/{id}`  | Fetch one book                       |
| PUT    | `/books/{id}`  | Replace a book                       |
| DELETE | `/books/{id}`  | Delete a book                        |

Book payload:

```json
{
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441013593"
}
```

`title` and `author` are required; `year` and `isbn` are optional.

## Examples

```sh
curl -s http://localhost:8080/health

curl -s -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

curl -s 'http://localhost:8080/books?author=Frank%20Herbert'

curl -s http://localhost:8080/books/1

curl -s -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Revised)","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

curl -s -X DELETE http://localhost:8080/books/1
```

## Tests

```sh
mvn test
```

The integration tests start the server on an ephemeral port against a temporary SQLite database and exercise every endpoint, including validation errors and the author filter.

# Books API

A REST API for managing a book collection, built with Java 21, Javalin, and SQLite.

## Requirements
- Java 21+
- Maven 3.9+

## Build & Test
```bash
mvn test       # run tests
mvn package    # build jar
```

## Run
```bash
mvn exec:java -Dexec.mainClass=com.example.books.App
# or
java -cp "target/books-api-1.0.0.jar:$(mvn -q dependency:build-classpath -Dmdep.outputFile=/dev/stdout)" com.example.books.App
```

Environment variables:
- `PORT` (default `7070`)
- `DB_URL` (default `jdbc:sqlite:books.db`)

## Endpoints
| Method | Path          | Description                          |
|--------|---------------|--------------------------------------|
| GET    | `/health`     | Health check                         |
| POST   | `/books`      | Create a book                        |
| GET    | `/books`      | List books (optional `?author=`)     |
| GET    | `/books/{id}` | Get a book                           |
| PUT    | `/books/{id}` | Update a book                        |
| DELETE | `/books/{id}` | Delete a book                        |

Book body: `{"title": "...", "author": "...", "year": 2020, "isbn": "..."}`. `title` and `author` are required.

## Example
```bash
curl -X POST localhost:7070/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"978-0441172719"}'
curl localhost:7070/books?author=Herbert
```

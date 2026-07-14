# Books API

A small REST API for managing a book collection, built with Java 21+, Javalin, and SQLite.

## Requirements
- Java 21+
- Maven 3.9+

## Build & Test
```
mvn test
mvn package
```

## Run
```
mvn -q exec:java -Dexec.mainClass=com.example.books.App
# or
java -jar target/books-api-1.0.0.jar
```

Environment variables:
- `PORT` — default `7070`
- `DB_URL` — default `jdbc:sqlite:books.db`

## Endpoints
- `GET /health` — health check
- `POST /books` — create (JSON: `title`, `author`, `year`, `isbn`; title and author required)
- `GET /books` — list all; `?author=Name` filters by author
- `GET /books/{id}` — fetch one
- `PUT /books/{id}` — update
- `DELETE /books/{id}` — delete

## Example
```
curl -X POST localhost:7070/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"978-0441172719"}'
```

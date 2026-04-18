# Books API

A REST API for managing a book collection, built with Java + Javalin + SQLite.

## Requirements
- Java 17+
- Maven 3.8+

## Build
```
mvn -q package
```

## Run
```
mvn -q exec:java -Dexec.mainClass=com.example.App
# or
java -jar target/books-api.jar
```

The service listens on port `7070` by default. Override with `PORT` and `BOOKS_DB` env vars.

## Endpoints
| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/books` | Create a book (`title`, `author` required) |
| GET | `/books` | List books, optional `?author=` filter |
| GET | `/books/{id}` | Get one book |
| PUT | `/books/{id}` | Update a book |
| DELETE | `/books/{id}` | Delete a book |

### Example
```
curl -X POST localhost:7070/books -H 'Content-Type: application/json' \
     -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"123"}'
```

## Test
```
mvn -q test
```

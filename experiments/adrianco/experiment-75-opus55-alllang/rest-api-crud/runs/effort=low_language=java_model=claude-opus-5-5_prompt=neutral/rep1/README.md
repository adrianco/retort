# Books REST API (Java)

A small REST service for a book collection, built on the JDK's built-in `HttpServer`, SQLite (`sqlite-jdbc`) and Jackson.

## Requirements
- JDK 21+
- Maven 3.9+

## Run
```sh
mvn -q compile exec:java          # listens on :8080, stores data in ./books.db
PORT=9000 DB_PATH=/tmp/b.db mvn -q compile exec:java
```

## Test
```sh
mvn test
```

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | body `{title, author, year?, isbn?}` → 201 |
| GET | /books | optional `?author=` filter (case-insensitive exact match) |
| GET | /books/{id} | 200 or 404 |
| PUT | /books/{id} | full replace, same validation → 200 / 400 / 404 |
| DELETE | /books/{id} | 204 or 404 |

`title` and `author` are required non-blank strings; `year` must be an integer. Errors return `{"error": "..."}` with 400/404/405.

Example:
```sh
curl -X POST localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'
```

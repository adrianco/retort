# Books REST API (Java)

Book collection service using the JDK built-in `HttpServer`, SQLite (`sqlite-jdbc`) and Jackson.

## Requirements
- Java 21+, Maven 3.9+

## Run
```
mvn -q compile exec:java          # listens on :8080, stores data in ./books.db
PORT=9000 DB_PATH=/tmp/b.db mvn -q compile exec:java
```

## Test
```
mvn test
```

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | /health | `{"status":"ok"}` |
| POST | /books | body `{title, author, year?, isbn?}` → 201 |
| GET | /books | optional `?author=` exact-match filter |
| GET | /books/{id} | 200 or 404 |
| PUT | /books/{id} | full replace, same validation as POST → 200/404 |
| DELETE | /books/{id} | 204 or 404 |

Validation errors return 400 with `{"errors":[...]}`; `title` and `author` are required non-blank strings, `year` must be an integer.

Example:
```
curl -X POST localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

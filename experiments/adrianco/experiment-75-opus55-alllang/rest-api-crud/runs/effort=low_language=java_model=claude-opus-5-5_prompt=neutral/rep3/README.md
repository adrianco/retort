# Books API

A small REST service (Java 21+, JDK HttpServer, SQLite via sqlite-jdbc, Jackson) for managing a book collection.

## Run
```
mvn -q compile exec:java          # listens on :8080, stores data in books.db
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
| POST | /books | body `{title, author, year, isbn}`; title & author required → 201 / 400 |
| GET | /books | optional `?author=` exact-match filter |
| GET | /books/{id} | 200 / 404 |
| PUT | /books/{id} | full replace, same validation → 200 / 400 / 404 |
| DELETE | /books/{id} | 204 / 404 |

Example:
```
curl -X POST localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

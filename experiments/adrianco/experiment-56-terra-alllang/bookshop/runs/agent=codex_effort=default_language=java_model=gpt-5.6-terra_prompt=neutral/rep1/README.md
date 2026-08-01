# Book Collection API

A Java 21 REST service built with Javalin and SQLite.

## Run

```bash
mvn test
mvn package
java -jar target/book-api-1.0.0.jar
```

The API listens on `http://localhost:7000` and stores data in `books.db`. Set `BOOKS_DB_URL` to use another JDBC SQLite URL, for example `jdbc:sqlite:/tmp/books.db`.

## Endpoints

- `GET /health` returns `{ "status": "ok" }`.
- `POST /books` creates a book. JSON fields: `title` and `author` (required), plus optional `year` and `isbn`.
- `GET /books` lists books; use `?author=Name` to filter by exact author.
- `GET /books/{id}` gets one book.
- `PUT /books/{id}` replaces a book using the same JSON fields as create.
- `DELETE /books/{id}` deletes a book.

Example:

```bash
curl -X POST http://localhost:7000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'
```

Successful creation returns `201`, deletion returns `204`, missing books return `404`, and invalid required fields return `400`. All endpoint responses are JSON (except the empty `204` response).

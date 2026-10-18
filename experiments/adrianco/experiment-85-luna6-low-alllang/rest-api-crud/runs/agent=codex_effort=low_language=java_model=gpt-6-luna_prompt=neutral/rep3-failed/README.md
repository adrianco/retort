# Book Collection API

A Java 17 Spring Boot REST API backed by SQLite.

## Run

Requirements: Java 17+ and Maven 3.9+.

```sh
mvn spring-boot:run
```

The service listens on `http://localhost:8080`; SQLite data is stored in `books.db` in the current directory. Set `BOOKS_DB_URL` to change the JDBC URL.

## API

- `POST /books` with JSON `{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }` creates a book (201).
- `GET /books` lists all books; `GET /books?author=Frank%20Herbert` filters by exact author, case-insensitively.
- `GET /books/{id}` reads one book (404 if absent).
- `PUT /books/{id}` replaces the book fields; title and author are required.
- `DELETE /books/{id}` removes a book (204, or 404 if absent).
- `GET /health` returns `{ "status": "ok" }`.

Invalid or missing title/author values return 400.

## Test

```sh
mvn test
```

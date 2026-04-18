# Book Collection REST API

A Spring Boot REST API for managing a book collection, backed by an embedded SQLite database.

## Requirements

- Java 17+
- Maven 3.6+

## Setup and Run

```bash
# Build the project
mvn package -q

# Run the application
java -jar target/books-0.0.1-SNAPSHOT.jar
```

The server starts on `http://localhost:8080`. The SQLite database is stored as `books.db` in the working directory.

## API Endpoints

### Health Check

```
GET /health
```

Response: `{"status": "ok"}`

### Create a Book

```
POST /books
Content-Type: application/json

{"title": "Clean Code", "author": "Robert Martin", "year": 2008, "isbn": "978-0132350884"}
```

- `title` and `author` are required; returns `400` if missing.
- Returns `201 Created` with the created book (including assigned `id`).

### List All Books

```
GET /books
GET /books?author=Robert+Martin
```

- Optional `author` query parameter filters results (case-insensitive).
- Returns `200 OK` with a JSON array.

### Get a Book by ID

```
GET /books/{id}
```

- Returns `200 OK` with the book, or `404 Not Found`.

### Update a Book

```
PUT /books/{id}
Content-Type: application/json

{"title": "New Title", "author": "New Author", "year": 2024, "isbn": "000-000"}
```

- Returns `200 OK` with the updated book, or `404 Not Found`.

### Delete a Book

```
DELETE /books/{id}
```

- Returns `204 No Content`, or `404 Not Found`.

## Running Tests

```bash
mvn test
```

12 integration tests cover all endpoints, including validation, filtering, and error cases.

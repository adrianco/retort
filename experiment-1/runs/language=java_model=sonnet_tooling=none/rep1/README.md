# Book Collection REST API

A Spring Boot REST API for managing a book collection, backed by a SQLite database.

## Requirements

- Java 17+
- Maven 3.6+

## Setup and Run

```bash
# Build the project
mvn package -DskipTests

# Run the application
java -jar target/book-collection-0.0.1-SNAPSHOT.jar
```

The server starts on `http://localhost:8080`. The SQLite database is stored in `books.db` in the working directory.

## Run Tests

```bash
mvn test
```

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

{"title": "Clean Code", "author": "Robert Martin", "year": 2008, "isbn": "9780132350884"}
```
- `title` and `author` are required; `year` and `isbn` are optional.
- Returns `201 Created` with the created book.

### List All Books
```
GET /books
GET /books?author=Robert Martin
```
- Optional `?author=` query parameter filters by author (case-insensitive).

### Get a Book by ID
```
GET /books/{id}
```
- Returns `404 Not Found` if the book does not exist.

### Update a Book
```
PUT /books/{id}
Content-Type: application/json

{"title": "New Title", "author": "New Author", "year": 2024}
```

### Delete a Book
```
DELETE /books/{id}
```
- Returns `204 No Content` on success.
- Returns `404 Not Found` if the book does not exist.

## Example with curl

```bash
# Create
curl -s -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Pragmatic Programmer","author":"Andy Hunt","year":1999}'

# List
curl -s http://localhost:8080/books

# Filter by author
curl -s "http://localhost:8080/books?author=Andy+Hunt"

# Get by ID
curl -s http://localhost:8080/books/1

# Update
curl -s -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title","author":"Andy Hunt"}'

# Delete
curl -s -X DELETE http://localhost:8080/books/1
```

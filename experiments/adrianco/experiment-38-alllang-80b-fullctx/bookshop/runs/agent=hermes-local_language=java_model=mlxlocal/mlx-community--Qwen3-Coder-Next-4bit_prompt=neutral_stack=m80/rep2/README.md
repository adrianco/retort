# Book API REST Service

A REST API service for managing a book collection built with Java, Jetty, Jackson, and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Requirements

- Java 17 or higher
- Gradle 7.0 or higher

## Building

```bash
./gradlew build
```

## Running

### Starting the Server

```bash
./gradlew run
```

The server will start on port 8080.

### Running as a JAR

```bash
./gradlew jar
java -jar build/libs/book-api-1.0-SNAPSHOT-all.jar
```

## API Usage Examples

### Health Check

```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "status": "healthy",
  "service": "Book API"
}
```

### Create a Book

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
  }'
```

### List All Books

```bash
curl http://localhost:8080/books
```

### List Books by Author

```bash
curl "http://localhost:8080/books?author=F.%20Scott%20Fitzgerald"
```

### Get Book by ID

```bash
curl http://localhost:8080/books/1
```

### Update a Book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby (Updated)",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
  }'
```

### Delete a Book

```bash
curl -X DELETE http://localhost:8080/books/1
```

## Testing

Run all tests:

```bash
./gradlew test
```

Run tests with verbose output:

```bash
./gradlew test --info
```

## Project Structure

```
src/
├── main/
│   └── java/com/example/
│       ├── BookApiApplication.java    # Main application entry point
│       ├── model/
│       │   └── Book.java              # Book entity
│       ├── repository/
│       │   └── BookRepository.java    # Database access layer
│       └── service/
│           └── BookService.java       # Business logic
└── test/
    └── java/com/example/
        ├── model/
        │   └── BookTest.java
        ├── repository/
        │   └── BookRepositoryTest.java
        └── service/
            └── BookServiceTest.java
```

## Database

The application uses SQLite as the embedded database. The database file `books.db` will be created in the current working directory when the application starts.

## License

MIT License

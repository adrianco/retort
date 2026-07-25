# Book API REST Service

A REST API service for managing a book collection using Spring Boot, Spring Data JPA, and SQLite.

## Features

- **POST /api/books** - Create a new book (title, author, year, isbn)
- **GET /api/books** - List all books (support ?author= filter)
- **GET /api/books/{id}** - Get a single book by ID
- **PUT /api/books/{id}** - Update a book
- **DELETE /api/books/{id}** - Delete a book
- **GET /api/books/health** - Health check endpoint

## Requirements

- Java 17 or higher
- Maven 3.6 or higher

## Setup

1. Clone the repository (or navigate to the project directory)
2. Build the project:
   ```bash
   mvn clean install
   ```

## Running

Run the application:
```bash
mvn spring-boot:run
```

Or run the JAR file:
```bash
java -jar target/book-api-1.0-SNAPSHOT.jar
```

The application will start on port 8080.

## Configuration

The application uses SQLite by default. You can configure the database location in `src/main/resources/application.properties`:

```properties
spring.datasource.url=jdbc:sqlite:books.db
spring.datasource.driver-class-name=org.sqlite.JDBC
spring.jpa.database-platform=org.hibernate.community.dialect.SQLiteDialect
spring.jpa.hibernate.ddl-auto=update
```

## API Usage Examples

### Create a book
```bash
curl -X POST http://localhost:8080/api/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "1984",
    "author": "George Orwell",
    "year": 1949,
    "isbn": "978-0451524935"
  }'
```

### Get all books
```bash
curl http://localhost:8080/api/books
```

### Get books by author
```bash
curl http://localhost:8080/api/books?author=George%20Orwell
```

### Get a specific book
```bash
curl http://localhost:8080/api/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/api/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "1984 (Updated)",
    "author": "George Orwell",
    "year": 1949,
    "isbn": "978-0451524935"
  }'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/api/books/1
```

### Health check
```bash
curl http://localhost:8080/api/books/health
```

## Testing

Run the tests:
```bash
mvn test
```

## Project Structure

```
src/
├── main/
│   └── java/com/bookapi/
│       ├── BookApiApplication.java       # Main application class
│       ├── controller/
│       │   └── BookController.java       # REST API endpoints
│       ├── dto/
│       │   ├── BookRequest.java          # Request DTO
│       │   └── BookResponse.java         # Response DTO
│       ├── entity/
│       │   └── Book.java                 # JPA entity
│       ├── repository/
│       │   └── BookRepository.java       # JPA repository
│       └── service/
│           ├── BookService.java          # Business logic
│           └── ResourceNotFoundException.java
└── test/
    └── java/com/bookapi/
        ├── controller/
        │   └── BookControllerTest.java   # Integration tests
        ├── dto/
        │   └── BookRequestTest.java      # Validation tests
        └── repository/
            └── BookRepositoryTest.java     # Repository tests
```

## License

MIT

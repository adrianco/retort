# Book API REST Service

A REST API service for managing a book collection, built with Spring Boot and SQLite.

## Requirements

- Java 17 or higher
- Maven 3.6+

## Setup and Run

1. Clone or navigate to the project directory.

2. Build the project:
   ```bash
   mvn clean package
   ```

3. Run the application:
   ```bash
   mvn spring-boot:run
   ```

   Or run the generated JAR:
   ```bash
   java -jar target/book-api-1.0.0.jar
   ```

The server will start on `http://localhost:8080`.

## API Endpoints

### Health Check
- `GET /health` - Returns the health status of the service.

### Books
- `POST /books` - Create a new book. Request body: `{ "title": "...", "author": "...", "year": ..., "isbn": "..." }`
- `GET /books` - List all books. Optionally filter by author: `?author=F. Scott Fitzgerald`
- `GET /books/{id}` - Get a single book by ID. Returns 404 if not found.
- `PUT /books/{id}` - Update an existing book. Request body: `{ "title": "...", "author": "...", "year": ..., "isbn": "..." }`
- `DELETE /books/{id}` - Delete a book by ID. Returns 204 on success, 404 if not found.

### Input Validation

- `title` and `author` are required fields when creating or updating a book.
- If validation fails, a 400 Bad Request response with field error details is returned.

### HTTP Status Codes

- `201 Created` - Book successfully created
- `200 OK` - Book successfully retrieved or updated
- `204 No Content` - Book successfully deleted
- `400 Bad Request` - Validation error or invalid input
- `404 Not Found` - Book not found

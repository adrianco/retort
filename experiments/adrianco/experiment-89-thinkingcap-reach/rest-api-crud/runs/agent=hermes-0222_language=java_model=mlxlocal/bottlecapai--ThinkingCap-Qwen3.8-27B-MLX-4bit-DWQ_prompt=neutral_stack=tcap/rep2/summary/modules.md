# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main/java/com/example/books/BookApplication.java | Spring Boot entry point | `BookApplication`, `main()` |
| src/main/java/com/example/books/Book.java | Book POJO model (id, title, author, year, isbn) | `Book` |
| src/main/java/com/example/books/BookRepository.java | SQLite access via Spring `JdbcTemplate` | `save`, `findAll`, `findByAuthor`, `findById`, `update`, `deleteById` |
| src/main/java/com/example/books/BookController.java | REST endpoints + input validation | `health`, `create`, `list`, `get`, `update`, `delete` |
| src/main/java/com/example/books/GlobalExceptionHandler.java | Maps exceptions to JSON error bodies + status codes | `handleResponseStatus`, `handleUnreadable`, `handleTypeMismatch`, `handleValidation` |
| src/main/resources/schema.sql | `books` table DDL, run on startup | — |
| src/main/resources/application.properties | Port, SQLite datasource, SQL init | — |
| src/test/resources/application.properties | Test datasource (target/test-books.db) | — |
| src/test/java/com/example/books/BookApiIntegrationTest.java | MockMvc integration tests | 14 `@Test` methods |
| pom.xml | Maven build: Spring Boot 3.5.16, sqlite-jdbc 3.50.3.0, JDK 17 | — |

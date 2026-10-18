# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main/java/com/example/books/Main.java | Process entry point; reads PORT/DB_PATH env, wires repository + server, installs shutdown hook | `main(String[])` |
| src/main/java/com/example/books/BookServer.java | HTTP front end on JDK `HttpServer`; routing, JSON (de)serialization, status codes | `BookServer`, `start(int)`, `stop()` |
| src/main/java/com/example/books/BookRepository.java | JDBC/SQLite persistence; CRUD + author filter + liveness ping | `BookRepository(String)`, `create`, `findById`, `findAll`, `update`, `delete`, `ping` |
| src/main/java/com/example/books/BookValidator.java | Static input validation (title/author required, year/isbn well-formed) | `validate(Book)` |
| src/main/java/com/example/books/Book.java | Immutable record for a book | `Book`, `withId(long)` |
| src/test/java/com/example/books/BookApiTest.java | End-to-end tests: real HTTP server on ephemeral port + real SQLite file | 13 `@Test` methods |

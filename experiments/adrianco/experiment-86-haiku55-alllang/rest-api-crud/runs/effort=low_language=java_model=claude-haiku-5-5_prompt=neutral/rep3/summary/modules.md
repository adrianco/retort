# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main/java/com/example/books/App.java | Entry point; wires repository + server, reads PORT/BOOKS_DB_PATH env | `App.main()` |
| src/main/java/com/example/books/BookServer.java | JDK HttpServer front end, routing, JSON (de)serialization, error mapping | `BookServer(port, repo)`, `start()`, `stop()`, `port()` |
| src/main/java/com/example/books/BookRepository.java | SQLite-backed CRUD storage over a shared JDBC connection | `insert`, `findById`, `findAll`, `update`, `delete`, `close` |
| src/main/java/com/example/books/BookValidator.java | Request validation + normalization, ISBN-10/13 check digits | `BookValidator.validate()`, `isValidIsbn()` |
| src/main/java/com/example/books/Book.java | Stored/returned book record | `Book` (record) |
| src/main/java/com/example/books/BookRequest.java | Client-supplied create/update payload record | `BookRequest` (record) |
| src/test/java/com/example/books/BookApiTest.java | End-to-end HTTP + repository + validator tests | 12 test methods |

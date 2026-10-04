# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main/java/books/App.java | Entry point: reads PORT/DB_PATH env, wires repo + server | `main()` |
| src/main/java/books/Book.java | Immutable book record (id, title, author, year, isbn) | `Book`, `withId()` |
| src/main/java/books/BookRepository.java | SQLite-backed storage, schema creation, CRUD + ping | `create`, `list`, `find`, `update`, `delete`, `ping` |
| src/main/java/books/BookServer.java | JDK HttpServer: routing, JSON, validation, error mapping | `BookServer`, `start`, `stop`, `port` |
| src/test/java/books/BookRepositoryTest.java | Repository persistence tests | 2 test methods |
| src/test/java/books/BookApiTest.java | End-to-end HTTP tests on ephemeral port | 11 test methods |

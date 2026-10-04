# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main/java/books/Main.java | Entry point; reads PORT/BOOKS_DB env, wires repo + server | `main()` |
| src/main/java/books/Book.java | Immutable book record | `Book` (record), `withId()` |
| src/main/java/books/BookRepository.java | SQLite persistence (JDBC), CRUD + author filter | `create`, `list`, `find`, `update`, `delete`, `close` |
| src/main/java/books/BookServer.java | JDK HttpServer; routing, validation, JSON rendering | `BookServer`, `start`, `stop`, `port` |
| src/test/java/books/BookApiTest.java | End-to-end HTTP tests over in-memory SQLite | 10 `@Test` methods |

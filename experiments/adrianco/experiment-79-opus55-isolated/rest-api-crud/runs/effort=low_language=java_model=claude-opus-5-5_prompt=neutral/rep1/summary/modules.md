# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main/java/com/example/books/App.java | Javalin HTTP server, route handlers, request parsing/validation, error mapping | `main()`, `create(BookRepository)` |
| src/main/java/com/example/books/BookRepository.java | SQLite-backed CRUD storage over a single JDBC connection | `create`, `list`, `find`, `update`, `delete`, `close` |
| src/main/java/com/example/books/Book.java | Immutable book record | `Book(id,title,author,year,isbn)` |
| src/test/java/com/example/books/AppTest.java | HTTP integration tests against a real server on a random port with in-memory SQLite | 10 `@Test` methods |

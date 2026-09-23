# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main/java/books/App.java | HTTP server (JDK `HttpServer`), routing, validation, JSON I/O | `App(port, dbUrl)`, `start()`, `stop()`, `port()`, `main()` |
| src/main/java/books/BookRepository.java | SQLite persistence via JDBC (schema + CRUD) | `BookRepository(url)`, `create`, `list`, `find`, `update`, `delete` |
| src/test/java/books/AppTest.java | HTTP integration tests against a live server on an ephemeral port | 5 `@Test` methods |
| pom.xml | Maven build (Java 21, sqlite-jdbc, Jackson, JUnit 5) | — |
| README.md | Setup, run, test, endpoint docs | — |

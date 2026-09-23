# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main/java/books/App.java | JDK HttpServer, routing, JSON I/O, request validation | `App(port, dbUrl)`, `start()`, `stop()`, `port()`, `main()` |
| src/main/java/books/BookRepository.java | SQLite persistence layer (JDBC), CRUD queries | `Book` record, `create`, `list`, `get`, `update`, `delete` |
| src/test/java/books/AppTest.java | HTTP integration tests against a live server | 4 test methods |

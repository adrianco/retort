# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main/java/com/example/books/BookApp.java | Entry point; boots `com.sun.net.httpserver` HTTP server, wires store + handler | `main` |
| src/main/java/com/example/books/BookApiHandler.java | HTTP routing + JSON response rendering for all routes | `handle` |
| src/main/java/com/example/books/BookStore.java | SQLite-backed repository (JDBC), lock-serialized CRUD | `BookStore`, `create`, `list`, `get`, `update`, `delete`, `close` |
| src/main/java/com/example/books/BookValidation.java | Validates title/author required, trims fields | `validate`, `require` |
| src/main/java/com/example/books/Json.java | Jackson JSON write / body parse helpers | `write`, `readBookInput`, `error` |
| src/main/java/com/example/books/Book.java | Persisted book record | `Book` (record) |
| src/main/java/com/example/books/BookInput.java | Client payload record (ignores unknown fields) | `BookInput` (record) |
| src/main/java/com/example/books/BookException.java | RuntimeException carrying an HTTP status | `BookException`, `status` |
| src/test/java/com/example/books/BookApiIntegrationTest.java | End-to-end HTTP tests over a real server + temp DB | 14 test methods |
| src/test/java/com/example/books/BookStoreTest.java | Unit tests for the SQLite repository | 9 test methods |
| src/test/java/com/example/books/BookValidationTest.java | Unit tests for validation + JSON parsing | 9 test methods |

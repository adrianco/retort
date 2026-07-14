# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/index.ts | Boots the HTTP server on PORT (default 3000) | `server` (default export) |
| src/app.ts | Express app: JSON parsing, `/health`, mounts `/books`, error handler | `app` (default export) |
| src/routes/books.ts | Router wiring routes to controller with validation middleware | `router` (default export) |
| src/controllers/BookController.ts | Request handlers for CRUD + author filter | `BookController` (static methods) |
| src/database/BookRepository.ts | Thin repository delegating to the in-memory store | `BookRepository`, `bookRepository` |
| src/database/Database.ts | In-memory array store with optional JSON-file persistence | `DatabaseManager`, `db` |
| src/models/Book.ts | Book interfaces and create/update validators | `Book`, `BookInput`, `BookUpdate`, `validateBookInput`, `validateBookUpdate` |
| src/middleware/validation.ts | Express middleware wrapping model validators | `validateBookCreate`, `validateBookUpdate` |
| tests/unit.test.ts | Unit tests | 12 test cases |
| tests/integration.test.ts | Integration tests (supertest) | 13 test cases |
| tests/__mocks__/database.ts | Jest mock of db + bookRepository | `db`, `bookRepository` (mocked) |

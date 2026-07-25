# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| Sources/App/entrypoint.swift | Executable `@main`; boots the Vapor app | `Entrypoint.main()` |
| Sources/App/configure.swift | Wires JSON coders, SQLite DB, migrations, routes | `configure(_:databasePath:)`, `configureJSONCoders()` |
| Sources/App/routes.swift | Registers `/health` and the `BookController` collection | `routes(_:)` |
| Sources/App/Models/Book.swift | Fluent model + public-response projection | `Book`, `Book.response` |
| Sources/App/Migrations/CreateBook.swift | Schema migration for the `books` table | `CreateBook` |
| Sources/App/DTOs/BookDTOs.swift | Request/response DTOs + validation logic | `BookRequest`, `BookResponse`, `ValidatedBook`, `BookRequest.validated(now:)` |
| Sources/App/Controllers/BookController.swift | CRUD route handlers for `/books` | `BookController`, `index`/`create`/`show`/`update`/`delete` |
| Sources/App/Controllers/HealthController.swift | `/health` route handler | `HealthController.health` |
| Tests/AppTests/BookAPITests.swift | End-to-end CRUD/filter API tests | 18 test functions |
| Tests/AppTests/BookValidationTests.swift | Unit tests for payload validation | 7 test functions |
| Tests/AppTests/HealthTests.swift | Health-endpoint test | 1 test function |
| Tests/AppTests/TestHelpers.swift | App bootstrap helper w/ isolated temp SQLite | `withApp(_:)` |

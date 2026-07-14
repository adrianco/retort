# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/app.ts | Express app factory with all CRUD + health routes, SQLite-backed, input validation | `buildApp(db)`, `Book` (interface) |
| src/server.ts | Entry point — opens `books.db`, builds app, starts listening | (top-level bootstrap) |
| src/api.test.ts | Supertest integration tests covering every endpoint | 13 `it()` tests across 6 `describe` blocks |

# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/index.ts | Express app bootstrap, /health route, server listen | `app` (default export) |
| src/routes.ts | CRUD route handlers for /books | `router` (default export) |
| src/database.ts | better-sqlite3 connection + `books` table schema | `getDb()`, `resetDb()` |
| src/middleware.ts | Input validation + error handling + JSON body parsing | `validateBook()`, `validatePartialBook()`, `handleError()`, `parseBody()` |
| src/types.ts | TypeScript interfaces | `Book`, `CreateBookInput`, `UpdateBookInput`, `ValidationError` |
| src/__tests__/books.test.ts | Integration tests over a live http server | 14 `it` tests |

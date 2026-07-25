# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/index.ts | Express HTTP server + all book route handlers | `app` (default export) |
| src/database.ts | SQLite connection + `books` table migration | `getDb(dbPath?)` |
| src/index.test.ts | Supertest API integration tests | 3 test functions |

# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.ts | Express app factory: SQLite schema, validation, all CRUD + health routes, error handler | `createApp(databasePath)` → `{ app, close }`, `validate()` |
| server.ts | Process entry: reads `PORT`/`DB_PATH`, starts listener, wires SIGINT/SIGTERM shutdown | top-level script |
| app.test.ts | In-process integration tests exercising Express via Node HTTP objects (no port) | 6 `node:test` tests, `fixture()` |

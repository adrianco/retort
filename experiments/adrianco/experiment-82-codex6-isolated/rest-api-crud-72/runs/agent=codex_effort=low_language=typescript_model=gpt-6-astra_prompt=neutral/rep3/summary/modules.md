# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.ts | Express app factory, SQLite schema, route handlers, validation, error middleware | `createApp()`, `Book`, `validateBook()` |
| server.ts | HTTP bootstrap: reads PORT/DATABASE_PATH env, listens, graceful shutdown | (module side effects) |
| app.test.ts | node:test integration tests exercising the middleware stack without a network port | 5 test functions |
| README.md | Setup/run instructions and API reference | — |
| package.json / tsconfig.json | Build (tsc), test (node --test), TS config (strict, NodeNext) | — |

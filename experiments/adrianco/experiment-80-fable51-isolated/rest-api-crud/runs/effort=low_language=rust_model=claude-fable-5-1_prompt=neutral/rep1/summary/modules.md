# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | HTTP server, route handlers, SQLite persistence, validation | `app()`, `open_db()`, `Book` |
| src/main.rs | Binary entry point: reads env, binds listener, serves `app` | `main()` |
| tests/api.rs | HTTP integration tests via `tower::oneshot` | 8 test functions |

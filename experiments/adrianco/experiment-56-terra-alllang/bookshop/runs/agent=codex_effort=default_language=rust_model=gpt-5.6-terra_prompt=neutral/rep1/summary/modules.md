# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | HTTP router, handlers, SQLite state, validation, tests | `app()`, `AppState`, `Book`, `BookInput` |
| src/main.rs | Binary: open DB, bind port, serve | `main()` |
| tests (in src/lib.rs `#[cfg(test)]`) | axum integration tests via `oneshot` | 4 test functions |

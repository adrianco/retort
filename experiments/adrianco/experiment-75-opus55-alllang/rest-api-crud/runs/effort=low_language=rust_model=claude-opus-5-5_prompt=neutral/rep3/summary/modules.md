# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | Axum app, handlers, DB access, validation, error type | `app`, `open_db`, `Book`, `BookInput`, `ApiError`, `Db` |
| src/main.rs | Binary entry: reads env, opens DB, binds, serves | `main` |
| tests/api.rs | Integration tests over the router (in-memory SQLite) | 4 `#[tokio::test]` functions |

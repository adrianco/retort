# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | Library crate: HTTP router, handlers, DB open/schema, validation, error type | `app()`, `open_db()`, `Book`, `BookInput`, `ApiError`, `Db` |
| src/main.rs | Binary entry point: reads env config, opens DB, binds listener, serves router | `main()` |
| tests/api.rs | Integration tests exercising the full router over in-memory SQLite | 7 `#[tokio::test]` functions |

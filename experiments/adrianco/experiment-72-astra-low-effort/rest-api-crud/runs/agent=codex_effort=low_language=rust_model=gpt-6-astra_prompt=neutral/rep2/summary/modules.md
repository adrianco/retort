# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib.rs | Axum router, handlers, SQLite access, error type | `app()`, `Database`, `Book`, `BookInput`, `ApiError` |
| main.rs | Binary entry: opens DB, binds TCP, serves with graceful shutdown | `main()` |
| tests.rs | Integration tests over the in-memory/file-backed app | 7 `#[tokio::test]` functions |
| Cargo.toml | Crate manifest (lib + bin + test targets) | — |
| README.md | Setup, run, API, and verify instructions | — |

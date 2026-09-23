# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | HTTP server, route handlers, DB open + schema, validation | `app()`, `open_db()`, `Book`, `BookInput`, `Db` |
| src/main.rs | Binary entrypoint: reads env, opens DB, binds and serves | `main()` |
| tests/api.rs | Integration tests over the in-memory app via `tower::oneshot` | 4 test functions |

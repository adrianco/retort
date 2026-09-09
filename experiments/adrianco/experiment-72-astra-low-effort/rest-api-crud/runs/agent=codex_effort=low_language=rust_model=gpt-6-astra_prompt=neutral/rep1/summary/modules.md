# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib.rs | Axum router, handlers, SQLite access, error type, validation | `app`, `Database`, `Book` |
| main.rs | Binary entry point: env config, bind, serve with graceful shutdown | `main` |
| tests/api.rs | HTTP integration tests over the in-process router | 5 test functions |

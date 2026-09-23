# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BookAPI.h | Public interface: response wrapper + API + server entry | `BAResponse`, `BookAPI`, `BARunServer()` |
| src/BookAPI.m | SQLite-backed CRUD handler + minimal HTTP/1.1 server | `-initWithDatabasePath:`, `-handleMethod:target:body:`, `BARunServer()` |
| src/main.m | Process entry point; reads PORT/DB_PATH env, starts server | `main()` |
| tests/test_main.m | In-memory integration tests exercising every endpoint | `main()` (21 CHECK assertions) |

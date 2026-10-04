# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/api.c | Routing, JSON parse/serialize, validation, SQLite access | `api_handle()`, `api_open_db()` |
| src/api.h | Public interface for the request handler and DB opener | `api_handle`, `api_open_db` |
| src/main.c | POSIX-socket HTTP/1.1 server; request parsing and I/O | `main()`, `handle_client()` |
| tests/test_api.c | In-process handler tests against `:memory:` DB | 7 test functions (49 checks) |
| tests/smoke.sh | End-to-end test: starts server, drives it with curl | shell script |

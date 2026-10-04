# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.c | JSON parse/serialize, book validation, SQLite access, request routing | `app_handle()`, `app_open_db()` |
| app.h | Public interface between the app layer and the HTTP server | `response_t`, `app_handle()`, `app_open_db()` |
| server.c | Single-threaded HTTP/1.1 server (POSIX sockets) and `main` | `main()` |
| test_app.c | Handler-level tests against an in-memory SQLite database | 7 test functions, 47 checks |
| test_http.sh | End-to-end test: starts the real server, drives it with curl | 9 curl checks |
| Makefile | Build/test targets | `all`, `test`, `clean` |
| README.md | Setup, run, and API documentation | — |

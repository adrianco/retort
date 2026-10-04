# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.cpp | Process entry: reads HOST/PORT/DB_PATH env vars, wires store→app→server, handles SIGINT/SIGTERM | `main()` |
| src/app.hpp / src/app.cpp | Transport-independent request routing, validation, and JSON serialization of books | `App`, `App::handle`, `Request`, `Response` |
| src/store.hpp / src/store.cpp | SQLite-backed persistence (RAII prepared statements, mutex-guarded) | `BookStore`, `create`, `list`, `get`, `update`, `remove`, `Book`, `BookData` |
| src/server.hpp / src/server.cpp | Blocking HTTP/1.1 server, thread-per-connection, `Connection: close` | `Server`, `start`, `stop`, `port` |
| src/json.hpp / src/json.cpp | Dependency-free JSON parser and string escaper | `json::parse`, `json::quote`, `json::Value` |
| tests/tests.cpp | Handler-level + end-to-end socket tests with a custom CHECK harness | 11 test functions, `main()` |

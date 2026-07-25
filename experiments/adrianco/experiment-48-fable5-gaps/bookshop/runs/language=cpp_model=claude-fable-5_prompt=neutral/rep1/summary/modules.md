# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.cpp | Executable entry; parses port/db from env+argv, starts httplib server | `main()` |
| src/api.h / src/api.cpp | HTTP route registration + JSON (de)serialization + validation | `register_routes()` |
| src/book_store.h / src/book_store.cpp | SQLite-backed CRUD store, thread-safe (mutex), RAII prepared statements | `BookStore`, `Book` |
| tests/test_api.cpp | Integration tests over a real server on an ephemeral port | 8 test functions |
| third_party/httplib.h, json.hpp | Vendored header-only deps (not evaluated) | — |

# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/books_api_app.erl | OTP application; starts store + Cowboy listener, compiles routes | `start/2`, `stop/1` |
| src/books_api_handler.erl | Cowboy HTTP handler; routing, JSON encode/decode, validation | `init/2`, `validate/1` |
| src/books_api_store.erl | gen_server persistence layer; shells out to `sqlite3` | `start_link/0`, `create/1`, `list/1`, `get/1`, `update/2`, `delete/1` |
| src/books_api.app.src | Application resource file (deps, env: port 8080, db books.db) | `books_api` |
| test/books_api_tests.erl | EUnit tests: validation + store CRUD + unknown-book | 3 test functions |

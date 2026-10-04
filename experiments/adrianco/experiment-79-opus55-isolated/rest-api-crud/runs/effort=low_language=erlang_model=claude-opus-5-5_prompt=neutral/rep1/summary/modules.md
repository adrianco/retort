# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/books_app.erl | OTP application callback; compiles routes, starts supervisor + Cowboy listener | `start/2`, `stop/1`, `routes/0` |
| src/books_sup.erl | Supervisor owning the DB gen_server; reads `db_path` env | `start_link/0`, `init/1` |
| src/books_db.erl | SQLite-backed storage; single gen_server owns the connection | `create/1`, `list/0,1`, `get/1`, `update/2`, `delete/1`, `start_link/1` |
| src/books_handler.erl | Cowboy handler for /books collection + item; body reading, JSON, validation | `init/2`, `reply/3`, `validate/1` |
| src/books_health_handler.erl | Cowboy handler for /health | `init/2` |
| src/books.app.src | Application resource file (deps, mod) | — |
| test/books_SUITE.erl | Common Test integration suite; boots app, exercises HTTP API via httpc | 12 test cases |
| test/books_validate_tests.erl | EUnit unit tests for `books_handler:validate/1` | 6 test functions |

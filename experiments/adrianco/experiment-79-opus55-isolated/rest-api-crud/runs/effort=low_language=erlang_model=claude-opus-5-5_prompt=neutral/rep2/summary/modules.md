# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/books_app.erl | OTP application: starts supervisor and Cowboy listener, compiles routes | `start/2`, `stop/1` |
| src/books_sup.erl | Supervisor owning the DB gen_server | `start_link/0`, `init/1` |
| src/books_db.erl | gen_server owning the SQLite (esqlite3) connection; serialises all DB access | `create/1`, `list/1`, `get/1`, `update/2`, `delete/1`, `delete_all/0` |
| src/books_handler.erl | Cowboy handler: routing dispatch, JSON decode, validation, responses | `init/2`, `validate/1` |
| src/books.app.src | Application resource file (deps, env: port, db_path) | — |
| test/books_api_tests.erl | EUnit integration tests over HTTP + unit tests for `validate/1` | `api_test_/0`, `validate_test_/0` |

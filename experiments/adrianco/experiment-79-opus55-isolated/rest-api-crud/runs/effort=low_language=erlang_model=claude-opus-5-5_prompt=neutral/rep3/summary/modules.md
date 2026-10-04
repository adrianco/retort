# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/book_api_app.erl | OTP application: starts sup, compiles Cowboy routes, binds HTTP listener | `start/2`, `stop/1`, `port/0` |
| src/book_api_sup.erl | Supervisor for the `book_store` gen_server (resolves DB file from env) | `start_link/0`, `init/1` |
| src/book_api_books_handler.erl | Cowboy handler for `/books` and `/books/:id`; request parsing, validation, JSON responses | `init/2`, `reply/3`, `method_not_allowed/2`, `validate/1` |
| src/book_api_health_handler.erl | Cowboy handler for `/health` | `init/2` |
| src/book_store.erl | DETS-backed storage gen_server; serialised CRUD + id counter | `create/1`, `list/0`, `list/1`, `get/1`, `update/2`, `delete/1`, `clear/0` |
| src/book_api.app.src | Application resource file (deps, env defaults) | — |
| test/book_api_tests.erl | EUnit HTTP integration tests + `validate/1` unit tests | 12 integration + 3 validate tests |

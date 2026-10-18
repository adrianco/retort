# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/books_app.erl | OTP application: compiles Cowboy routes, starts supervisor + listener | `start/2`, `stop/1` |
| src/books_sup.erl | Supervisor for the storage gen_server | `start_link/1`, `init/1` |
| src/books_http.erl | Cowboy handler for `/health`, `/books`, `/books/:id` | `init/2` |
| src/books_store.erl | DETS-backed storage gen_server (CRUD + author filter) | `start_link/1`, `create/1`, `get/1`, `list/1`, `update/2`, `delete/1` |
| src/books_validate.erl | Payload validation + normalisation | `validate/1` |
| src/books.app.src | Application resource file (deps, env defaults) | — |
| test/books_api_tests.erl | End-to-end HTTP tests on an ephemeral port | 8 test generators |
| test/books_store_tests.erl | Storage gen_server unit tests (incl. restart persistence) | 6 test generators |
| test/books_validate_tests.erl | Validation unit tests | 11 `*_test` functions |

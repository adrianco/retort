# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/books_app.erl | OTP application + supervisor; boots store and HTTP listener | `start/2`, `stop/1`, `init/1` |
| src/books_http.erl | Minimal HTTP/1.1 server on `gen_tcp` (no external deps); parses request, dispatches, serialises JSON | `start_link/1`, `init/1`, `port/0` |
| src/books_api.erl | Routing, request validation and status/JSON mapping | `handle/4`, `validate/1` |
| src/books_store.erl | `gen_server` persistence backed by DETS (embedded disk DB) | `start_link/1`, `create/1`, `list/1`, `get/1`, `update/2`, `delete/1` |
| src/books.app.src | Application resource file (env: port, db_file) | `books` app spec |
| test/books_tests.erl | EUnit validation unit tests + HTTP integration tests | `validate_test_/0`, `api_test_/0` (health, crud, filter, invalid) |

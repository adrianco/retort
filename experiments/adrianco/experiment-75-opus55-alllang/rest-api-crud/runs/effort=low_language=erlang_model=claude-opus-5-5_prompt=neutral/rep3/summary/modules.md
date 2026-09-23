# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/books_app.erl | OTP application + supervisor booting the DB and HTTP children | `start/2`, `stop/1`, `init/1` |
| src/books_http.erl | Minimal HTTP/1.1 server on `gen_tcp` (one process per connection) | `start_link/1`, `port/0`, `accept_loop/1`, `handle_conn/1` |
| src/books_api.erl | Routing, JSON body validation, request handling | `handle/3`, `validate/1` |
| src/books_db.erl | DETS-backed embedded storage as a `gen_server` | `start_link/1`, `create/1`, `list/1`, `get/1`, `update/2`, `delete/1` |
| src/books.app.src | Application resource file (env: port 8080, db_file books.dets) | application `books` |
| test/books_tests.erl | EUnit unit + integration tests | `validate_test_/0`, `api_test_/0` |

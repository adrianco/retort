# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/books_app.erl | OTP application: starts supervisor + Cowboy listener, resolves port/db from env | `start/2`, `stop/1`, `port/0`, `db_path/0` |
| src/books_sup.erl | Supervisor owning the DB gen_server | `start_link/1` |
| src/books_db.erl | SQLite-backed gen_server; schema, CRUD, ping | `insert/1`, `list/1`, `get/1`, `update/2`, `delete/1`, `ping/0` |
| src/books_validate.erl | Pure payload validation/normalisation | `validate/1` |
| src/books_http.erl | Shared handler helpers: JSON reply, body parse, row↔JSON, id parse | `reply_json/3`, `reply_error/3`, `read_json_body/1`, `book_to_json/1`, `parse_id/1` |
| src/books_collection_handler.erl | /books Cowboy handler (GET list + ?author=, POST create) | `init/2` |
| src/books_item_handler.erl | /books/{id} Cowboy handler (GET, PUT, DELETE) | `init/2` |
| src/books_health_handler.erl | /health Cowboy handler | `init/2` |
| src/books.app.src | Application resource file | — |
| test/books_api_tests.erl | End-to-end HTTP tests via httpc against the running app | 10 test bodies in one generator |
| test/books_validate_tests.erl | Unit tests for the validation module | 8 test functions |

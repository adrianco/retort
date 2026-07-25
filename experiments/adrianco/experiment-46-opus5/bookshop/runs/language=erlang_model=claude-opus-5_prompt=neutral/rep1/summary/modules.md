# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/book_api_app.erl | Application callback: starts Mnesia + Cowboy listener; defines routes and port config | `start/2`, `stop/1`, `port/0`, `routes/0` |
| src/book_api_sup.erl | Root supervisor (currently no children; well-formed tree only) | `start_link/0`, `init/1` |
| src/book.erl | Pure domain logic: JSON payload validation and book→map rendering (no side effects) | `validate/1`, `to_map/1`, `matches_author/2` |
| src/book_store.erl | Persistence layer over Mnesia `disc_copies` (book + book_counter tables) | `init/1`, `stop/0`, `create/1`, `list/0`, `list_by_author/1`, `get/1`, `update/2`, `delete/1`, `count/0` |
| src/book_api_http.erl | Shared request/response plumbing: JSON encode, body decode, error envelope, id parsing, crash guard | `json/3`, `error/4`, `error/5`, `method_not_allowed/2`, `read_json_body/1`, `parse_id/1`, `handle/2` |
| src/book_api_books_h.erl | Cowboy handler for `/books` collection (GET list + ?author filter, POST create) | `init/2` |
| src/book_api_book_h.erl | Cowboy handler for `/books/:id` (GET, PUT, DELETE) | `init/2` |
| src/book_api_health_h.erl | Cowboy handler for `GET /health` (touches DB for readiness) | `init/2` |
| src/book_api_notfound_h.erl | Catch-all handler returning JSON 404 for unmatched routes | `init/2` |
| src/book_api.app.src | OTP application resource file (deps, mod, env: port 8080, db_dir "data") | (app metadata) |
| include/book_api.hrl | `#book{}` record definition (Mnesia-keyed shape) | `book` record |
| config/sys.config | Release/runtime config | (config) |
| test/book_tests.erl | EUnit unit tests for `book` validation/rendering | 20 `*_test/0` functions |
| test/book_store_tests.erl | EUnit tests for Mnesia store incl. durability | `store_test_/0`, `durability_test_/0` (generators) |
| test/book_api_http_tests.erl | EUnit integration tests driving the live HTTP API | `api_test_/0` (generator) |
| test/book_api_test_helper.erl | Test support: start/stop app, fresh DB, HTTP request helpers | `start_app/0`, `stop_app/1`, `get/1`, `post/2`, `put/2`, `delete/1`, `request/…`, `url/1`, `reset_db/0`, `encode_body/1`, `decode_body/1` |

Build files (not source): rebar.config, rebar.lock, README.md.

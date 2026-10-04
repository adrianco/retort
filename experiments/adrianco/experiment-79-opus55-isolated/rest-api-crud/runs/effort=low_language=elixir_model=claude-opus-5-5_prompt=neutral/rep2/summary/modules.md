# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib/book_api/application.ex | OTP application; starts the Store and (outside tests) the Bandit HTTP server | `BookApi.Application.start/2` |
| lib/book_api/router.ex | Plug router; HTTP routes, request parsing, error handling | route matchers, `handle_errors/2` |
| lib/book_api/store.ex | SQLite-backed persistence; a GenServer owning one connection | `list/1`, `get/1`, `create/1`, `update/2`, `delete/1`, `delete_all/0` |
| lib/book_api/book.ex | Validation of incoming book payloads | `BookApi.Book.validate/1` |
| config/config.exs | Compile-time config (db path, port, test overrides) | — |
| config/runtime.exs | Runtime env overrides (`DATABASE_PATH`, `PORT`) | — |
| test/book_api_test.exs | Integration tests driving the router via `Plug.Test` | 18 test cases |
| test/test_helper.exs | ExUnit bootstrap | `ExUnit.start()` |

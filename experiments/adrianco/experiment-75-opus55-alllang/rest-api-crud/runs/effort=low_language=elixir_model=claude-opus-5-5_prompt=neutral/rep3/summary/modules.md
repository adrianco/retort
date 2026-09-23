# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib/books/application.ex | OTP application; starts Repo + Bandit HTTP server under a supervisor | `Books.Application.start/2` |
| lib/books/router.ex | Plug.Router; HTTP routes, JSON encoding, error handling | `Books.Router` (get/post/put/delete routes) |
| lib/books/repo.ex | SQLite-backed storage; GenServer serialising one exqlite connection | `Books.Repo` — `list/1`, `get/1`, `create/1`, `update/2`, `delete/1`, `reset/0` |
| lib/books/validator.ex | Validates/normalises book params (title & author required) | `Books.Validator.validate/1` |
| test/books_test.exs | Plug.Test integration tests for the router | 5 test functions |
| test/test_helper.exs | ExUnit bootstrap | `ExUnit.start/0` |
| config/config.exs | Base config (db_path, port, server) + env import | — |
| config/{dev,prod,test}.exs | Per-env config; test uses `:memory:` DB, server disabled | — |
| mix.exs | Project + deps (plug, bandit, jason, exqlite) | `Books.MixProject` |

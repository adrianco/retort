# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib/books/router.ex | Plug.Router HTTP routes, request validation, JSON encoding | `Books.Router` (Plug), `validate/1` |
| lib/books/repo.ex | SQLite-backed storage serialized through a GenServer | `Books.Repo` — `start_link/1`, `list/1`, `get/1`, `create/1`, `update/2`, `delete/1`, `reset/0` |
| lib/books/application.ex | OTP application: starts Repo + Bandit HTTP server under a supervisor | `Books.Application.start/2` |
| mix.exs | Project + deps (bandit, plug, jason, exqlite) | `Books.MixProject` |
| config/config.exs | Base config: db_path, port, server flag from env | — |
| config/test.exs | Test config: in-memory SQLite, server disabled | — |
| config/dev.exs, config/prod.exs | Env config stubs (empty) | — |
| test/router_test.exs | Plug.Test integration tests for all routes | 5 test blocks |
| test/test_helper.exs | ExUnit bootstrap | `ExUnit.start()` |

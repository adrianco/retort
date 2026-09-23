# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib/books/router.ex | Plug.Router HTTP routes + request validation | `Books.Router`, `validate/1` |
| lib/books/repo.ex | SQLite-backed storage GenServer (single serialized connection) | `Books.Repo`, `list/1`, `get/1`, `create/1`, `update/2`, `delete/1`, `reset/0` |
| lib/books/application.ex | OTP application; supervises Repo + optional Cowboy server | `Books.Application.start/2` |
| mix.exs | Project + deps (plug_cowboy, jason, exqlite) | `Books.MixProject` |
| config/config.exs | Base config (db_path, port, server), imports env config | — |
| config/test.exs | Test config: in-memory SQLite, server disabled | — |
| test/books_test.exs | Plug.Test integration tests over the router | 5 test functions |

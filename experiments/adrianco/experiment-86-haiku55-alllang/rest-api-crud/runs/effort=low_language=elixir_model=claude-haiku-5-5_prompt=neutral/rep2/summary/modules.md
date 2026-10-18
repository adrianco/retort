# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib/books_api/application.ex | OTP application; starts Repo + Bandit HTTP server | `BooksApi.Application.start/2` |
| lib/books_api/router.ex | Plug.Router HTTP routes, JSON encoding, status codes | `BooksApi.Router` (`get`/`post`/`put`/`delete`) |
| lib/books_api/book.ex | Validation + persistence logic for books | `list/1`, `get/1`, `create/1`, `update/2`, `delete/1`, `validate/1` |
| lib/books_api/repo.ex | GenServer owning a single SQLite connection | `BooksApi.Repo.start_link/1`, `query/3` |
| test/books_api_test.exs | Router-level integration tests | 8 test functions |
| config/config.exs | Base config (port, database_path, logger) | — |
| config/test.exs | Test config (port 0, `:memory:` DB) | — |
| config/dev.exs | Empty dev config | — |

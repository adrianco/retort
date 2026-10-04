# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib/book_api/application.ex | OTP application; supervises Store + Bandit HTTP server | `start/2` |
| lib/book_api/router.ex | Plug.Router HTTP routes, JSON encoding, error mapping | route handlers, `json/3` (priv) |
| lib/book_api/store.ex | GenServer owning the SQLite connection; all CRUD SQL | `create/1`, `list/1`, `get/1`, `update/2`, `delete/1`, `clear/0` |
| lib/book_api/book.ex | Validation of incoming book payloads | `validate/1` |
| config/config.exs | Compile-time config | (config) |
| config/runtime.exs | Runtime config (port, db path from env) | (config) |
| test/router_test.exs | Router integration tests via Plug.Test | 14 test cases |
| test/test_helper.exs | ExUnit bootstrap | (setup) |

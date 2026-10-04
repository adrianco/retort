# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Stdlib HTTP server, SQLite store, route handlers, validation | `validate_book`, `BookStore`, `BookHandler`, `create_server()`, `main()` |
| test_app.py | Integration tests against the real server on an ephemeral port | 13 test functions (one parametrized ×7) |
| README.md | Setup, run, endpoint, and validation documentation | — |
| requirements-dev.txt | Dev dependency pin (`pytest`) | — |

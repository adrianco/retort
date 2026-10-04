# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Stdlib HTTP server, routing, validation, SQLite store | `create_server()`, `main()`, `BookStore`, `BookHandler`, `validate_book()`, `ApiError` |
| test_app.py | HTTP integration tests driving a real ephemeral server | 18 test functions (several parametrized) |
| README.md | Setup, run, and API documentation | — |
| requirements-dev.txt | Test-only dependency (`pytest`) | — |

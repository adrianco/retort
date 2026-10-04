# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | HTTP server, routing, validation, and SQLite storage — the whole service in one module | `validate_book()`, `BookStore`, `BookRequestHandler`, `create_server()`, `main()` |
| test_app.py | Integration tests: a real server on an ephemeral port, real HTTP requests | 25 test functions (39 cases with parametrization) |
| README.md | Setup, run, and API documentation | — |
| requirements-dev.txt | Dev dependency pin (`pytest` only) | — |
| .gitignore | Ignores build/db artifacts | — |

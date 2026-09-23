# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Stdlib HTTP server, validation, SQLite repository, routing | `validate_book()`, `BookRepository`, `BookAPIHandler`, `make_server()`, `main()` |
| test_app.py | Unit tests (validation, repository) + HTTP integration tests | 24 `test_*` functions (one parametrized ×10) |
| README.md | Setup, run, and API documentation | — |
| requirements-dev.txt | Test-only dependency (`pytest>=8`) | — |

Runtime code uses only the Python standard library (`http.server`, `sqlite3`,
`json`, `argparse`); no third-party runtime dependency.

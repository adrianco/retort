# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| bookapi.py | Stdlib HTTP server, SQLite store, routing, validation | `BookStore`, `validate_book`, `Handler`, `make_server`, `main` |
| tests/test_api.py | End-to-end API tests against a live in-memory server | 11 test functions (2 parametrized) |
| README.md | Setup, run, endpoint and error documentation | — |

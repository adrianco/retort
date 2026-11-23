# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| Books.m | Single-file Objective-C HTTP service: SQLite access, routing, HTTP request/response, TCP accept loop | `main()`, `serve()`, `request()`, `route()`, `query()` |
| test_books.py | Python `unittest` integration tests driving `./books --stdio` | `BookAPI` (4 test methods) |
| Makefile | Build (`clang -fobjc-arc -framework Foundation -lsqlite3`) and `make test` | `books`, `test`, `clean` |
| README.md | Setup/run instructions + route table | — |

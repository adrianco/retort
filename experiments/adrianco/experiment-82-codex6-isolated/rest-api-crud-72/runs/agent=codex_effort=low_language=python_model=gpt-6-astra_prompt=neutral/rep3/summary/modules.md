# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Dependency-free WSGI book API backed by SQLite: request parsing/validation, routing, SQL persistence, JSON responses, CLI server | `BookAPI`, `create_app()`, `read_book()`, `main()` |
| test_app.py | unittest integration suite driving the WSGI app in-process and over a real HTTP socket | `BookAPITests` (8 test methods) |
| README.md | Setup/run instructions, route table, validation rules, curl examples | — |

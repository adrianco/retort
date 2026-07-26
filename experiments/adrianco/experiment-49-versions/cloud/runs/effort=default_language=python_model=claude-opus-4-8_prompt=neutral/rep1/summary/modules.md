# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP layer, SQLite persistence, validation | `create_app()`, `get_db()`, `init_db()`, `validate_book_payload()`, `book_to_dict()` |
| test_app.py | Integration tests against isolated temp DBs | 12 test functions, `client` fixture |
| requirements.txt | Dependencies | Flask>=2.3, pytest>=7.0 |
| README.md | Setup, run, and API documentation | — |

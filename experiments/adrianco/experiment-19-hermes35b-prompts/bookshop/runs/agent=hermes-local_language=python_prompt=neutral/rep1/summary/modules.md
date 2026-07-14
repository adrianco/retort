# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLAlchemy `Book` model, route handlers | `app`, `db`, `Book`, `init_db()` |
| test_app.py | Pytest integration tests over the API | 14 test functions, `client`/`sample_book` fixtures |
| README.md | Setup, run, and API usage documentation | — |
| books.db | SQLite database file (build artifact) | — |

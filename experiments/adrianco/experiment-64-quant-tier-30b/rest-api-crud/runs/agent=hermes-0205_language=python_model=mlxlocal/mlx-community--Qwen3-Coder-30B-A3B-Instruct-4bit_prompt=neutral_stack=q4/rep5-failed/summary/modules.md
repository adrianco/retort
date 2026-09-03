# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.py | FastAPI app; the app the README tells you to run (`uvicorn main:app`) | `app`, `init_db()`, `health_check()`, `get_books()` |
| book_api.py | Plain-function SQLite CRUD layer — NOT wired to any HTTP route | `init_db()`, `create_book()`, `get_all_books()`, `get_book_by_id()`, `update_book()`, `delete_book()`, `health_check()`, `main()` |
| check_env.py | Prints Python version / path (debug scratch) | module script |
| test_book_api.py | HTTP integration tests against `main:app` (starts uvicorn at import) | 8 `test_*` functions |
| test_db.py | Direct sqlite smoke script (no assertions) | `test_database()` |
| test_simple.py | Direct sqlite smoke script (no assertions) | `test_database()` |

Two divergent implementations coexist: `book_api.py` holds the full CRUD logic as bare
functions, while `main.py` is the actual served FastAPI app but only exposes `/health` and
`GET /books`. The CRUD functions in `book_api.py` are never imported by `main.py`.

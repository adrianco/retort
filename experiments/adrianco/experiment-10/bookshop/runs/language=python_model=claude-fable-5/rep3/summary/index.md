# Architecture Summary: language=python_model=claude-fable-5 · rep3

## Modules

| File | Role | Lines |
|------|------|-------|
| `app.py` | Flask application — routes, validation, DB schema, entry point | 173 |
| `test_app.py` | pytest test suite — 10 integration tests via Flask test client | 117 |
| `requirements.txt` | Dependencies: flask>=3.0, pytest>=8.0 | 2 |
| `README.md` | Setup, run, and API documentation | 75 |

## Architecture

Single-module Flask app using the application-factory pattern (`create_app(db_path)`). All routes, validation, and DB access are co-located in `app.py`.

- **Persistence:** SQLite via `sqlite3` stdlib. Schema auto-created on app init (`app.py:24`). Per-request connection stored in Flask `g` context (`app.py:28-30`).
- **Validation:** Centralized `validate_payload()` (`app.py:48-82`) handles required-field and type checks for both create (full) and update (partial) flows.
- **Routing:** Six endpoints — CRUD on `/books`, `/books/{id}`, plus `/health`. All return JSON via `jsonify()`.
- **Error handling:** Custom 404/405 handlers return JSON instead of HTML.

## Data Flow

```
Client → Flask route → validate_payload() → sqlite3 → jsonify(row_to_dict()) → Response
```

## Test Strategy

Integration tests using Flask's `test_client()`. Each test gets a fresh SQLite DB in `tmp_path`. No mocking. Tests cover: health check, create, validation (missing fields, invalid year), list with author filter, get by id, 404 on missing, update (partial + validation), delete with re-delete 404.

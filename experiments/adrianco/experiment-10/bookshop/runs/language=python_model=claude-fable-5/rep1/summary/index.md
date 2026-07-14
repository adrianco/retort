# Architecture Summary: bookshop (Python/Flask)

## Modules

| File | Purpose | Lines |
|------|---------|-------|
| `app.py` | Flask application — routes, DB setup, validation | 173 |
| `test_app.py` | Integration tests using Flask test client | 111 |
| `requirements.txt` | Dependencies (flask, pytest) | 2 |
| `README.md` | Setup, API docs, examples | 77 |

## Architecture

Single-module Flask application using the factory pattern (`create_app()`). All routes, DB logic, and validation are co-located in `app.py`.

### Data Layer
- SQLite via `sqlite3` stdlib module (no ORM)
- Per-request connection via Flask's `g` object (`get_db()`)
- Schema auto-created on app startup (`app.py:37-40`)

### API Endpoints
- `GET /health` — health check
- `POST /books` — create with validation (title, author required)
- `GET /books` — list all, optional `?author=` filter
- `GET /books/{id}` — single book lookup
- `PUT /books/{id}` — partial update with validation
- `DELETE /books/{id}` — delete with 204/404

### Validation
- `validate_payload()` (`app.py:51-87`) handles both full and partial validation
- Type checking for year (int), isbn (string), title/author (non-empty strings)
- Returns structured error arrays

### Test Architecture
- Fixture-based: `tmp_path` for isolated DB per test
- `make_book()` helper for DRY test setup
- 8 tests covering all CRUD operations, validation, and health check

## Flow

```
HTTP Request → Flask route → validate_payload() → get_db() → SQLite → jsonify() → Response
```

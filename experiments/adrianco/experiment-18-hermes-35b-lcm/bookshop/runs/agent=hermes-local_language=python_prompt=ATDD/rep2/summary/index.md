# Architecture Summary — bookshop (hermes-local · python · ATDD · rep2)

> Generated inline by `evaluate-run`; the standalone `run-summary` skill is not
> available in this session (troubleshooting fallback).

## Modules

| File | Role |
|------|------|
| `app.py` | Flask application factory (`create_app`). Registers all routes, configures SQLite via SQLAlchemy, creates tables on startup. |
| `models.py` | `Book` SQLAlchemy model (`books` table) with `to_dict()` serializer. Imports `db` from `app`. |
| `test_app.py` | 24 client-only acceptance tests (pytest), one class per endpoint group + a lifecycle scenario. Fresh in-memory DB per test via fixture. |
| `requirements.txt` | flask 3.1.0, flask-sqlalchemy 3.1.1, pytest 8.3.4, requests 2.32.3. |

## Interfaces (HTTP)

- `GET /health` → `{"status":"ok"}` 200
- `POST /books` → 201 (validates title/author non-empty; 400 otherwise)
- `GET /books?author=` → 200 list (optional author filter)
- `GET /books/{id}` → 200 / 404
- `PUT /books/{id}` → 200 / 404 (partial updates supported)
- `DELETE /books/{id}` → 200 / 404

## Flow

`create_app()` → configure SQLite (`DATABASE_URI` env, default `sqlite:///books.db`)
→ `db.init_app` → `db.create_all()` → register route closures → return `app`.
Each route reads/writes via `Book.query` and `db.session`, returning `jsonify`
dicts built inline (the model's `to_dict()` is defined but unused).

## Notable

- The **application code is correct and complete** for all 6 CRUD endpoints +
  health + validation + SQLite persistence.
- The **acceptance suite is broken**: 16/24 tests POST/PUT with `data=<dict>` +
  `content_type="application/json"`, which sends a *form-encoded* body the JSON
  API rejects. Only the 2 tests using `json=` (and pure-GET/404 tests) pass.

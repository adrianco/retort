# Architecture Summary

> `run-summary` is not exposed as a callable Skill in this session; this concise
> summary was produced inline. The codebase is a single Flask module, so a full
> multi-file architecture breakdown is not warranted.

## Modules

| File | Role |
|------|------|
| `app.py` | Flask application: `Book` SQLAlchemy model + all 6 route handlers + `/health`. Creates tables at import time. |
| `run.py` | Thin launcher — imports `app` and runs the dev server on `0.0.0.0:5000`. |
| `test_app.py` | `unittest` suite (11 tests) driving the API via Flask's `test_client()`. |
| `README.md` | Setup, endpoint list, and curl usage examples. |
| `instance/books.db` | SQLite database file (build artifact). |

## Interfaces (REST contract)

- `POST /books` → 201 JSON book; 400 on missing title/author
- `GET /books` (`?author=`) → 200 JSON list
- `GET /books/{id}` → 200 JSON book; 404 if absent
- `PUT /books/{id}` → 200 JSON book; 400 on missing title/author; 404 if absent
- `DELETE /books/{id}` → 200 JSON message; 404 if absent
- `GET /health` → 200 `{"status": "healthy"}`

## Flow

Request → Flask route → SQLAlchemy `Book` model query/commit → `to_dict()` → `jsonify`.
Persistence is file-backed SQLite (`sqlite:///books.db`). Errors roll back the
session and return a JSON 5xx. Absent-resource paths use `get_or_404`, which
returns Flask's default **HTML** 404 page (not JSON).

## Notes

- Single-layer design: model + routes co-located in one 121-line module. Adequate
  for the task's scope; no service/repository separation.
- `Book` carries `created_at`/`updated_at` timestamps beyond the spec (enhancement).

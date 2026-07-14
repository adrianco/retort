# Architecture Summary

> `run-summary` skill was not invocable in this session; this is a lightweight
> inline summary written by `evaluate-run`.

## Modules

| File | Role |
|------|------|
| `app.py` | Entire service: `create_app()` factory, six REST routes, `Book` SQLAlchemy model, `to_dict()`, CLI entry point. |
| `tests/test_acceptance.py` | 27 black-box acceptance tests driving the HTTP surface via Flask test client (7 test classes, one per capability). |
| `tests/test_unit.py` | 8 unit tests: factory, route registration, `Book` model, `to_dict()`, DB integrity. |
| `README.md` | Setup/run/API/test documentation. |

## Interfaces (REST)

- `GET /health` → 200 `{"status":"healthy"}`
- `POST /books` → 201 (400 on missing/empty title|author)
- `GET /books` (`?author=` partial, case-insensitive) → 200 list
- `GET /books/<int:id>` → 200 | 404
- `PUT /books/<int:id>` → 200 | 404 | 400
- `DELETE /books/<int:id>` → 200 | 404

## Flow

`create_app()` builds a Flask app, binds Flask-SQLAlchemy to `sqlite:///books.db`
(overridden to in-memory `sqlite://` when `TESTING`), calls `db.create_all()`,
registers all routes as closures, and returns the app. Each route resolves the
`Book` by id via `db.session.get`, mutates through `db.session`, and serializes
inline dicts (route handlers do not reuse `Book.to_dict()`).

## Notes

- Application-factory pattern; single-file design appropriate to task scope.
- `Book.to_dict()` exists but route handlers hand-roll the same dict — mild duplication.
- `create_app()` reads `app.config["TESTING"]` at factory time (default `False`),
  so the persistent `instance/books.db` file is always created even under test;
  test fixtures override the URI *after* the factory returns.

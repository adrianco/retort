# Summary: agent=hermes-local language=python prompt=neutral · rep 1

- **Shape:** Flask REST API with Flask-SQLAlchemy over SQLite.
- **Structure:** 1 source module (`app.py`), 1 test module (`test_app.py`, 14 tests), README.
- **Interfaces:** 6 HTTP routes (full CRUD + `?author=` filter + `/health`); no CLI, no exported library API.
- **Notable:** Clean, idiomatic single-file Flask app; validation for required fields and year; missing `requirements.txt`; non-string title/author would 500 instead of 400.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

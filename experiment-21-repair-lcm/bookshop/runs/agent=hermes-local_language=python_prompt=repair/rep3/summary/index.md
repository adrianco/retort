# Summary: agent=hermes-local language=python prompt=repair · rep 3

- **Shape:** Flask REST API with raw `sqlite3` persistence (no ORM), single-module.
- **Structure:** 1 source module (`app.py`), 1 test file (`test_app.py`, 11 tests).
- **Interfaces:** 6 HTTP routes (5 CRUD on `/books` + `/health`); no CLI, no library API.
- **Notable:** Repair task — prior attempt had working `app.py` but no tests/README; this run added `test_app.py`, `README.md`, and `DATABASE_PATH` env-var support for test isolation. Goes beyond spec with ISBN-uniqueness 409 handling. `init_db()` runs on every request (minor inefficiency).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

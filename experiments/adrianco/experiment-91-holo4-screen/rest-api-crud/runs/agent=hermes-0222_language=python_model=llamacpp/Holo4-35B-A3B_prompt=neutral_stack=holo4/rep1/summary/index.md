# Summary: agent=hermes-0222 language=python model=llamacpp/Holo4-35B-A3B prompt=neutral stack=holo4 · rep 1

- **Shape:** Single-file Flask REST API with raw `sqlite3` persistence (no ORM).
- **Structure:** 1 source module (`app.py`), 1 test file (`tests/test_app.py`), 1 README.
- **Interfaces:** 6 HTTP routes (health + full CRUD on /books with `?author=` filter); 1 SQLite table.
- **Notable:** Clean, idiomatic Flask using `g` for per-request connections and `teardown_appcontext` for cleanup. Validation of required fields and year type. 9 tests cover every route including 404/400 paths.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

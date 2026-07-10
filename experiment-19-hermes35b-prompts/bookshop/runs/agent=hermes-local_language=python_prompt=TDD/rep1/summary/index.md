# Summary: agent=hermes-local language=python prompt=TDD · rep 1

- **Shape:** Flask REST API with raw `sqlite3` storage (no ORM).
- **Structure:** 1 source module (`app.py`), 2 test files + conftest.
- **Interfaces:** 6 HTTP routes, 3 library functions, 1 `books` table.
- **Notable:** Clean app-factory pattern; 20 tests, 0 skips, ~98% coverage. Full
  CRUD + author filter + validation + health all present. Minor rough edges: no
  connection teardown hook, DB path via `os.environ`, `PUT` assumes a JSON body.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

# Summary: effort=max language=python model=claude-haiku-5-5 prompt=neutral · rep 3

- **Shape:** Flask REST API with a blueprint, backed by SQLite via the stdlib `sqlite3` module (no ORM).
- **Structure:** 6 source modules + 2 test files (plus conftest); 304 source LOC, 380 test LOC.
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`); exported `create_app`, `validate_book`, `normalize_isbn`.
- **Notable:** Cleanly layered (routes → validation → repository → db); JSON error handling for `ApiError` and Werkzeug exceptions including 404/405; ISBN-10/13 checksum validation and case-insensitive author filtering go beyond the spec. 37 tests, zero skips.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

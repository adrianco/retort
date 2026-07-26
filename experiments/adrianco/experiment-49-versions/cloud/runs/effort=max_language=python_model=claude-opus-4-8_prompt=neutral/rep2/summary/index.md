# Summary: effort=max · python · claude-opus-4-8 · prompt=neutral · rep 2

- **Shape:** Flask REST API with standard-library `sqlite3` storage (no ORM, no external DB server).
- **Structure:** 2 source modules (app.py, test_app.py) + README + requirements.txt.
- **Interfaces:** 6 HTTP routes (full CRUD + `?author=` filter + `/health`); one `books` table.
- **Notable:** Application-factory pattern for hermetic tests; per-request connection via Flask `g`; case-insensitive author filter; JSON 404/405 error handlers; whitespace trimming and typed validation. Clean, idiomatic, well-documented.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

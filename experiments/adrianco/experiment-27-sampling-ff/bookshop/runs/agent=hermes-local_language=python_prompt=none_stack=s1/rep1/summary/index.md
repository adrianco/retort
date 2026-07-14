# Summary: agent=hermes-local · language=python · prompt=none · stack=s1 · rep 1

- **Shape:** Flask REST API over raw `sqlite3` (no ORM), single-file app.
- **Structure:** 1 source module (`app.py`), 1 test file (`test_app.py`, 18 tests).
- **Interfaces:** 6 HTTP routes (health + full book CRUD), `?author=` filter; `books` SQLite table with 5 columns.
- **Notable:** Uses Flask `g` + `teardown_appcontext` for per-request connections and WAL mode; validation covers required title/author and a bounded-int year; author filter is a substring `LIKE` match, not exact.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

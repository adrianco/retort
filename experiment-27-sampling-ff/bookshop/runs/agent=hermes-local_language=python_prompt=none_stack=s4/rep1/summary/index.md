# Summary: agent=hermes-local language=python prompt=none stack=s4 · rep 1

- **Shape:** Flask REST API with plain `sqlite3` (no ORM), per-request connection on Flask `g`.
- **Structure:** 1 source module (`app.py`), 1 test file (`test_app.py`, 17 tests / 7 classes), README.
- **Interfaces:** 6 HTTP routes (5 CRUD on `/books` + `/health`); 1 `books` table; no CLI, no library API.
- **Notable:** Complete CRUD with input validation and year-type coercion; PUT does partial updates; `?author=` uses substring `LIKE`. Clean, idiomatic, no skipped tests.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

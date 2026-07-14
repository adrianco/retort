# Summary: agent=hermes-local language=python prompt=none stack=s2 · rep 1

- **Shape:** Flask REST API backed by raw `sqlite3` (no ORM), single-file `app.py`.
- **Structure:** 1 source module, 1 test file (13 test functions across 6 classes).
- **Interfaces:** 6 HTTP routes (health + full books CRUD with `?author=` filter); no CLI; no exported library API.
- **Notable:** Minimal, self-contained two-file layout. Per-request connections cached on `g` with a teardown hook; parameterized SQL; schema auto-created at import. No handling for the `isbn` UNIQUE constraint (duplicate would 500), and empty-body POST/PUT yields 415 rather than a custom 400.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

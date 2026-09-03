# Summary: agent=hermes-0205 · python · Qwen3-Coder-30B-A3B-Instruct-8bit · prompt=neutral · stack=q8 · rep 1

- **Shape:** Single-file Flask REST API over raw `sqlite3` (no ORM, no blueprints, no app factory).
- **Structure:** 1 source module (`app.py`, 205 lines), 1 test file (`test_app.py`, 221 lines), 1 dependency.
- **Interfaces:** 6 HTTP routes, 1 SQLite table, no CLI or exported library API.
- **Notable:** The DB path is a module-level constant (`DATABASE = 'books.db'`) rather than Flask config, so the test fixture's `app.config['DATABASE']` override at `test_app.py:22` is dead — tests share one on-disk database and two of them fail on a clean checkout.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

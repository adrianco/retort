# Summary: agent=hermes-0205 · language=python · model=mlxlocal/Qwen3-Coder-30B-A3B-Instruct-6bit · prompt=neutral · stack=q6 · rep 3

- **Shape:** Single-module Flask REST API over raw `sqlite3` (no ORM, no blueprints).
- **Structure:** 1 source module (158 lines), 1 test file (190 lines, 10 tests), README + requirements.txt.
- **Interfaces:** 6 HTTP routes / 0 CLI commands / 1 SQLite table.
- **Notable:** Minimal dependency surface (`flask` only — pytest is used but unpinned); per-request
  connections; validation is presence-only; the test suite reuses the same `books.db` file the
  service writes to.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

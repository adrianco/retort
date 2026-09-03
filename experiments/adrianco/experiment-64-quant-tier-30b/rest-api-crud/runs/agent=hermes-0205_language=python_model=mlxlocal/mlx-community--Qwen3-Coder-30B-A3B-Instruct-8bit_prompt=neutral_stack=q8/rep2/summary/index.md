# Summary: agent=hermes-0205 · language=python · model=mlxlocal/Qwen3-Coder-30B-A3B-Instruct-8bit · prompt=neutral · stack=q8 · rep 2

- **Shape:** single-file Flask REST API over raw `sqlite3` (no ORM, no blueprints).
- **Structure:** 1 source module (203 lines), 1 test file (197 lines, 11 tests), README + pinned requirements.
- **Interfaces:** 6 HTTP routes / 0 CLI commands / 0 exported library functions; 1 SQLite table.
- **Notable:** complete spec coverage in ~200 lines; tests share the real on-disk `books.db` with no fixture teardown, so they are order-dependent by construction and pass only because every assertion is written defensively (`len(data) >= 1`).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

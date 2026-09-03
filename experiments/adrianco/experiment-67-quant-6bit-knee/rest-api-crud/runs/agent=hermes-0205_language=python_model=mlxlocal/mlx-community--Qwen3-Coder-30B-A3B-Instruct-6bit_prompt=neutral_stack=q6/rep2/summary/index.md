# Summary: agent=hermes-0205 · python · Qwen3-Coder-30B-A3B-Instruct-6bit · prompt=neutral · stack=q6 · rep 2

- **Shape:** single-file Flask REST API over raw `sqlite3` (no ORM), 6 routes.
- **Structure:** 1 source module (`app.py`, 207 lines), 1 test file (`test_app.py`, 284 lines, 14 tests), README + pinned `requirements.txt`.
- **Interfaces:** 6 HTTP routes / 0 CLI commands / 1 SQLite table.
- **Notable:** the DB path is captured in a module-level constant at import time, so `test_app.py`'s temp-file fixture never takes effect — all 14 tests share one on-disk `books.db` and 3 of them fail on leaked state. Validation is `.strip()`-based and crashes on non-string input.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

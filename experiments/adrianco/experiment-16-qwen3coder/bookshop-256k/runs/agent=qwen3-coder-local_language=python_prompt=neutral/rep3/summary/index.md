# Summary: agent=qwen3-coder-local language=python prompt=neutral · rep 3

- **Shape:** Flask REST API with raw `sqlite3` persistence (single-file `app.py`).
- **Structure:** 1 source module, 1 test file (11 tests), 1 README.
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`); no CLI, no library API.
- **Notable:** Idiomatic minimal Flask; per-request connections, DB-level ISBN
  uniqueness. Dev server launched with `debug=True` on `0.0.0.0`; README's
  port (5000) and dependency list (`aiosqlite`) do not match the code
  (port 5001, stdlib `sqlite3`).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

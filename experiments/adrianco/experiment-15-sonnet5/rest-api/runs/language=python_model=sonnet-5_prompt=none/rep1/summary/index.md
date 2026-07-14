# Summary: language=python model=sonnet-5 prompt=none · rep 1

- **Shape:** FastAPI REST API with a raw-`sqlite3` data-access layer (no ORM).
- **Structure:** 2 source modules (`main.py`, `database.py`) + 1 test file (`test_main.py`), README, requirements.
- **Interfaces:** 6 HTTP routes (health + full CRUD), 0 CLI commands, 7 DB helper functions.
- **Notable:** Clean separation of HTTP (Pydantic models + routes) from persistence; injectable DB path via `Depends(get_db_path)` makes tests hermetic (per-test tmp DB). Validation returns FastAPI's default 422 (not 400) for missing/blank fields.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

# Summary: agent=hermes-local language=python prompt=neutral · rep 2

- **Shape:** Flask REST API with raw `sqlite3` persistence (WAL mode), single-module.
- **Structure:** 1 app module, 1 test module (15 tests), 1 README.
- **Interfaces:** 6 HTTP routes (5 CRUD on `/books` + `/health`), 0 CLI commands, 0 exported library functions.
- **Notable:** Clean per-request connection handling via Flask `g`/`teardown_appcontext`; presence-only validation; broad `try/except → 500 {error: str(e)}` on every handler.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

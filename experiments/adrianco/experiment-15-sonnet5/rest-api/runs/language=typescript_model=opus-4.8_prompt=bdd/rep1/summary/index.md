# Summary: language=typescript_model=opus-4.8_prompt=bdd · rep 1

- **Shape:** TypeScript + Express CRUD API backed by Node's built-in `node:sqlite` (embedded, no native build step).
- **Structure:** 5 source modules + 1 test file (12 BDD tests).
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`), 1 SQLite table, 4 exported functions/classes.
- **Notable:** Clean layered design (db → repository → validation → app → server) with the DB injected into `createApp` for testability. Uses the very new `node:sqlite` builtin (requires Node 22.5+), loaded via `createRequire` so Vitest doesn't pre-resolve the builtin. `?author=` filter uses exact equality (`author = ?`), not a substring/case-insensitive match. Validation trims and normalises `year`/`isbn` types beyond the required title/author checks.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

# Summary: agent=codex effort=default language=typescript model=gpt-6-luna prompt=neutral · rep 2

- **Shape:** TypeScript CRUD API on Node's built-in `node:http` server with `node:sqlite` persistence — zero runtime dependencies.
- **Structure:** 3 source modules (`books.ts` core, `server.ts` entry, `books.test.ts` tests), 1 test file.
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), 1 exported factory (`createBookServer`).
- **Notable:** Uses the stdlib `node:sqlite` module (Node ≥22.5) rather than pulling `better-sqlite3` — no third-party deps at all. Manual routing via regex; author filter is case-insensitive (`COLLATE NOCASE`); 1 MB body cap; DI-friendly factory takes a DB path so tests use `:memory:`.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

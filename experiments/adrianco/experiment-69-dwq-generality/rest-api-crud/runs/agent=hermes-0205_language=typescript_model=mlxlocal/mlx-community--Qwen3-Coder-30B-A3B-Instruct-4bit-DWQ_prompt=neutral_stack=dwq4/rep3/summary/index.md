# Summary: agent=hermes-0205 · language=typescript · model=Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ · stack=dwq4 · rep 3

- **Shape:** Express 4 REST API over file-backed SQLite (`sqlite3` callback API), written as a single CommonJS **JavaScript** file — no TypeScript, despite `language=typescript`.
- **Structure:** 1 source module (`server.js`, 200 lines), 1 test file (`test.js`, 280 lines, 14 tests), 4 dependencies.
- **Interfaces:** 7 HTTP routes (6 spec routes + catch-all 404), 1 exported symbol (`app`), 1 table (`books`).
- **Notable:** All SQL is parameterized. Tests share one persistent `./books.db` with a no-op `beforeEach`, so cases are not isolated. Every prepared statement leaks (never finalized). The agent's own `SUMMARY.md` claims TypeScript and an in-memory database — both false.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

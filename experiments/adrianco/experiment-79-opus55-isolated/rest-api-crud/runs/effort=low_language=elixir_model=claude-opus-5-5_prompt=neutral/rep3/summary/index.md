# Summary: rest-api-crud · effort=low, model=claude-opus-5-5, prompt=neutral · rep 3

- **Shape:** Elixir Plug + Bandit REST API with SQLite (exqlite) persistence via a GenServer-owned connection.
- **Structure:** 4 source modules + 2 config files, 1 test file (14 test cases).
- **Interfaces:** 6 HTTP routes (+ catch-all 404); one `books` SQLite table.
- **Notable:** Serializes DB access through a single GenServer (no connection pool needed); explicit error taxonomy (400/404/413/422); validation trims whitespace; PUT is a full replace. Uses 422 (not 400) for validation failures — a defensible, RFC-aligned choice, documented in the README.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

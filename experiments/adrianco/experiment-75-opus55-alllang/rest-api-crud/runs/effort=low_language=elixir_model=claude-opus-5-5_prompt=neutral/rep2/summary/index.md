# Summary: effort=low_language=elixir_model=claude-opus-5-5_prompt=neutral · rep 2

- **Shape:** Elixir Plug + Cowboy REST API with SQLite persistence (Exqlite) behind a GenServer.
- **Structure:** 3 lib modules + 3 config files, 1 test file (5 tests).
- **Interfaces:** 6 HTTP routes (+ catch-all 404) / 0 CLI commands / 6 exported Repo functions.
- **Notable:** Idiomatic OTP design — a GenServer serializes the single SQLite connection; server startup is config-gated (`server: false` in tests) so integration tests hit the router directly via `Plug.Test`. Validation returns `422` (Unprocessable Entity) rather than `400`.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

# Summary: effort=low_language=erlang_model=claude-opus-5-5_prompt=neutral · rep 1

- **Shape:** Erlang/OTP REST API using Cowboy for HTTP and SQLite (esqlite NIF) for persistence, structured as a standard OTP application (app → supervisor → gen_server DB owner).
- **Structure:** 6 source modules, 2 test files (1 Common Test suite + 1 EUnit module).
- **Interfaces:** 6 HTTP routes (full CRUD on /books + ?author= filter + /health).
- **Notable:** Idiomatic OTP layout — a single gen_server serializes all DB access; parameterized SQL throughout (no injection); careful edge handling (body size cap, integer overflow guard on ids/year, 405 with Allow header, 413 on oversize body).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

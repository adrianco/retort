# Summary: python · hermes-0222 · ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ · neutral · tcap · rep 3

- **Shape:** Flask REST API with raw-`sqlite3` persistence (application-factory pattern).
- **Structure:** 1 source module (`app.py`), 1 test file (27 tests), `requirements.txt`, `README.md`.
- **Interfaces:** 6 HTTP routes (health + full CRUD) plus global JSON 404/405 handlers; one `books` table; one exported `create_app()` factory.
- **Notable:** Clean, idiomatic Flask; parameterized SQL (no injection); per-request connection on `g`; partial-update PUT with unknown-field rejection; validation distinguishes missing/blank/wrong-type. No pagination (not required).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

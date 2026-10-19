# Summary: java · hermes-0222 · ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ · neutral · tcap · rep 2

- **Shape:** Spring Boot 3 REST API with `JdbcTemplate` over a real SQLite file.
- **Structure:** 5 main Java classes + schema.sql + 2 property files; 1 test file (14 tests).
- **Interfaces:** 6 HTTP routes (full CRUD + health), JSON error envelope via `@RestControllerAdvice`.
- **Notable:** Clean layering (controller / repository / model / exception handler), null-safe `year` handling, case-insensitive author filter, non-numeric id → 400, malformed JSON → 400. No concurrency/pagination (not required).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

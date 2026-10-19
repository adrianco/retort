# Summary: agent=hermes-0222 language=java model=ThinkingCap-Qwen3.8-27B prompt=neutral stack=tcap · rep 1

- **Shape:** Java REST CRUD on the JDK's built-in `com.sun.net.httpserver`, SQLite via `sqlite-jdbc`, Jackson JSON, Maven + JUnit 5 — no web framework.
- **Structure:** 8 main modules + 3 test files (~880 LOC source).
- **Interfaces:** 6 HTTP routes (health + 5 CRUD, incl. `?author=` filter); `BookStore` repository API; one `books` table.
- **Notable:** Clean layering (handler / validation / store / JSON helpers), records for DTOs, lock-serialized single connection, 405/404/400/500 handled with `Allow` and `Location` headers. 32 tests, zero skipped.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

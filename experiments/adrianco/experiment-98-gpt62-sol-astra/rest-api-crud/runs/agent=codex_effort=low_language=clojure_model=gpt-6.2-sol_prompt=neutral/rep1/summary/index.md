# Summary: agent=codex effort=low language=clojure model=gpt-6.2-sol prompt=neutral · rep 1

- **Shape:** Clojure REST API — Ring/Jetty handler with raw `java.sql` JDBC over SQLite, Cheshire for JSON.
- **Structure:** 2 source modules (core, db), 1 test file (5 tests), ~163 source LOC.
- **Interfaces:** 6 HTTP routes (full books CRUD + `?author=` filter + `/health`); 1 `books` table.
- **Notable:** No ORM or `clojure.java.jdbc` wrapper — hand-rolled `PreparedStatement` helper with explicit null/string/long binding and `RETURNING *`. Per-call connections (no pool). Strict JSON parsing, `405`+`Allow` on wrong method, `500` on SQL errors. Clean, idiomatic-leaning but low-ceremony.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

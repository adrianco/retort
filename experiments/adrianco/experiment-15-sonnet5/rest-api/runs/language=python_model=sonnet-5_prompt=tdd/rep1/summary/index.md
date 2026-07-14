# Summary: language=python_model=sonnet-5_prompt=tdd · rep 1

- **Shape:** FastAPI REST API over raw `sqlite3`, with Pydantic validation and a clean 4-layer split (main / schemas / crud / database).
- **Structure:** 5 source modules, 6 test files (14 tests via a shared temp-DB fixture).
- **Interfaces:** 6 HTTP routes (full CRUD + `?author=` filter + `/health`); 1 SQLite table.
- **Notable:** Uses the standard-library `sqlite3` driver directly rather than an ORM — leaner than SQLAlchemy-based peers. Test isolation via env-var-overridable DB path is idiomatic. Fresh connection per CRUD call (no pooling), acceptable at this scale.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

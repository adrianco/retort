# Summary: language=python · model=sonnet-5 · prompt=bdd · rep 1

- **Shape:** FastAPI REST API with a hand-rolled SQLite (`sqlite3`) data layer and Pydantic v2 validation.
- **Structure:** 3 source modules (`main`, `database`, `schemas`) + 2 test files (12 tests total).
- **Interfaces:** 6 HTTP routes (5 CRUD on `/books` + `/health`); `books` SQLite table; 4 Pydantic models.
- **Notable:** Clean layered split (routes / persistence / schemas); BDD-named tests each on an isolated temp SQLite DB via dependency override; per-request connection + `init_db()`; validation returns `422` (FastAPI default) rather than `400`.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

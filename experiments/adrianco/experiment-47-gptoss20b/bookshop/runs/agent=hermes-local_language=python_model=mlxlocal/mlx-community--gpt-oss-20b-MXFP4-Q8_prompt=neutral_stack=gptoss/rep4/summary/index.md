# Summary: python · hermes-local · gpt-oss-20b · rep 4

- **Shape:** FastAPI REST API with SQLAlchemy ORM over SQLite.
- **Structure:** 4 source modules + 2 test files (main/database/models/schemas + conftest/test_api).
- **Interfaces:** 6 HTTP routes (5 CRUD on /books + /health), 4 Pydantic schemas, 1 ORM model.
- **Notable:** Clean idiomatic layering (app/db/model/schema split). Uses deprecated `@app.on_event("startup")` and Pydantic v1 `orm_mode`. Validation errors return 422, not the 400 the spec implies.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).

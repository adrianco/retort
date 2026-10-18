# Evaluation: rest-api-crud · agent=codex effort=low language=java model=gpt-6-luna prompt=neutral · rep 2

## Summary

- **Factors:** language=java, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral, framework=unknown (JDK `com.sun.net.httpserver` + SQLite JDBC)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective) — from `test_coverage=1.0`
- **Build:** pass (not re-run — `test_coverage=1.0` in `scores.json` ⇒ `mvn test` built + ran clean)
- **Lint:** pass — `code_quality=1.0` in `scores.json`
- **Architecture:** `run-summary` skill unavailable in this session; see inline note below.
- **Findings:** 0 items in `findings.jsonl`

## Requirements

Checklist from the pinned `REQUIREMENTS.json` (constant denominator = 12 for all runs of this task).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates (title, author, year, isbn) | ✓ implemented | `BookServer.java` POST branch → `store.create`; `BookStore.create` INSERTs all four fields |
| R2 | GET /books lists all | ✓ implemented | `BookServer.java` GET `/books` → `store.list(null)` → `SELECT * FROM books ORDER BY id` |
| R3 | GET /books ?author= filter | ✓ implemented | `store.list(author)` → `WHERE lower(author)=lower(?)`; test asserts filter returns 1 vs 0 |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `/books/` GET branch → `store.find(id)`, empty ⇒ 404; test asserts 200 then 404 after delete |
| R5 | PUT /books/{id} updates | ✓ implemented | PUT branch → `store.update`; test asserts title "Old"→"New" |
| R6 | DELETE /books/{id} | ✓ implemented | DELETE branch → `store.delete`, 204 / 404; test asserts 204 |
| R7 | SQLite / embedded DB | ✓ implemented | `pom.xml` `org.xerial:sqlite-jdbc`; `BookStore` uses `jdbc:sqlite:` + real table |
| R8 | JSON responses + proper status codes | ✓ implemented | Jackson serialization; 201/200/204/400/404/500 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `parse()` returns 400 "Title/Author is required"; test asserts 400 for `{"author":"A"}` |
| R10 | GET /health | ✓ implemented | `/health` branch returns `{"status":"ok"}`; test asserts 200 + "ok" |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — build, run, env vars, API, test instructions |
| R12 | >= 3 unit/integration tests | ✓ implemented | 3 `@Test` methods in `BookServerTest.java`; `test_coverage=1.0` |

No `P*` prompt requirements: the `neutral` prompt prescribes no methodology and only asks for tests (already R12).

## Build & Test

Not re-run per the evaluate-run skill — mechanical scores already computed and stored:

```text
scores.json: {"code_quality": 1.0, "token_efficiency": 0.0118, "test_coverage": 1.0,
              "defect_rate": 1.0, "maintainability": 0.7572, "idiomatic": 0.3}
```

`test_coverage=1.0` ⇒ `mvn test` compiled and all tests passed. `defect_rate=1.0` ⇒ build+test success.
(Run is not yet in `retort.db` — scored inline as a gate — so `scores.json` is authoritative.)

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, `*.java`) | 110 |
| Files (excl. build artifacts) | 13 |
| Dependencies (pom.xml) | 3 (sqlite-jdbc, jackson-databind, junit-jupiter) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| code_quality | 1.0 |
| maintainability | 0.757 |
| idiomatic | 0.30 |

## Architecture (inline note)

`run-summary` skill is not available in this session, so no `summary/` was produced. Brief structure:

- `Book.java` — immutable record (id, title, author, year, isbn).
- `BookStore.java` — SQLite persistence layer; opens a connection per operation, auto-creates the `books` table, CRUD + author filter via prepared statements.
- `BookServer.java` — JDK `HttpServer` with a single `/` context dispatching by path/method; Jackson for JSON; input validation via `parse()`; consistent JSON error envelopes.
- `BookServerTest.java` — 3 JUnit 5 integration tests driving a real server on an ephemeral port + temp-file SQLite DB over `java.net.http.HttpClient`.

Observations (not defects): `BookStore.list` carries an awkward no-op `if` branch but behaves correctly; PUT uses full-replace semantics (requires title+author), which satisfies the spec. The low `idiomatic=0.30` is a computed metric, not a correctness issue.

## Findings

None. All 12 requirements implemented, build + tests clean, no skipped/disabled tests. `findings.jsonl` is empty.

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=java_model=gpt-6-luna_prompt=neutral/rep2"
cat scores.json                               # stored mechanical scores (build/test/lint)
grep -rE "@Test" src/test --include="*.java" | wc -l    # 3
grep -rE "@Disabled|assumeTrue|@Ignore" src --include="*.java" | wc -l   # 0
find src -name "*.java" | xargs wc -l | tail -1          # 110
# To re-run from scratch (not required): mvn test
```

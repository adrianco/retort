# Evaluation: agent=codex_effort=low_language=java_model=gpt-6.1-terra_prompt=neutral · rep 1

## Summary

- **Factors:** language=java, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral, framework=Spring Boot 3.5.16
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from `test_coverage=1.0` (scores.json)
- **Lint:** pass — from `code_quality=1.0` (scores.json)
- **Architecture:** `run-summary` skill unavailable in this environment; summary omitted. Single-controller Spring Boot app: `BooksApplication` (entrypoint), `BookController` (all routes + validation + error handling), `schema.sql` (SQLite DDL), `application.properties` (datasource + schema init).
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `BookController.java:31-44` create(), INSERT + 201 + Location |
| R2 | GET /books lists all | ✓ implemented | `BookController.java:46-50` list(), SELECT * ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `BookController.java:49` WHERE author = ?; test `BookApiTest.java:35` |
| R4 | GET /books/{id} single book | ✓ implemented | `BookController.java:52-56` get(), 404 via ResponseStatusException |
| R5 | PUT /books/{id} update | ✓ implemented | `BookController.java:58-63` update(), UPDATE + 404 if no row |
| R6 | DELETE /books/{id} delete | ✓ implemented | `BookController.java:65-69` delete(), 204 + 404 if no row |
| R7 | SQLite / embedded DB storage | ✓ implemented | `application.properties:1` jdbc:sqlite; `schema.sql`; sqlite-jdbc in `pom.xml` |
| R8 | JSON responses + HTTP codes | ✓ implemented | 201/200/204/404/400 across controller; records serialized to JSON |
| R9 | Validation: title & author required | ✓ implemented | `BookController.java:25` @NotBlank; `:71-74` 400 handler; test `BookApiTest.java:50-52` |
| R10 | GET /health | ✓ implemented | `BookController.java:28-29` returns {"status":"ok"}; test `BookApiTest.java:53` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Java/Maven prereqs, mvn test/run/package, endpoints, env vars |
| R12 | ≥ 3 tests | ✓ implemented | 3 @Test methods in `BookApiTest.java`; test_coverage=1.0 |

## Build & Test

Not re-run — scores read from `scores.json` (inline gate output):

```text
test_coverage = 1.0   → build + all tests passed
code_quality  = 1.0   → lint/quality clean
defect_rate   = 1.0   → build+test succeeded
maintainability = 0.935
idiomatic     = 0.6
```

Tests: `BookApiTest` — MockMvc integration against an in-memory shared-cache SQLite datasource; 3 methods exercise create/get/filter/list, update/delete/404 paths, and validation/health. No `@Disabled`/`@Ignore`/`assumeTrue` skips found.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main Java, non-blank) | 73 |
| Total source lines (java+sql+properties) | 151 |
| Files (excl. target/.git) | 15 |
| Dependencies (pom) | 5 (web, jdbc, validation, sqlite-jdbc, test) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build/test signal | test_coverage=1.0 |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] R3 — `?author=` filter is exact and case-sensitive (documented; spec-compliant)
2. [info] R5 — PUT is a full replace; omitted year/isbn become null (documented; acceptable)

No correctness, build, test, or requirement defects. A clean, idiomatic Spring Boot CRUD implementation.

## Reproduce

```bash
cd "experiments/adrianco/experiment-92-terra61-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=java_model=gpt-6.1-terra_prompt=neutral/rep1"
cat scores.json                 # mechanical scores (build/test/lint), do not re-run
cat ../../REQUIREMENTS.json     # pinned 12-requirement checklist
grep -rE "@Disabled|@Ignore|assumeTrue" src/test   # skip detection (none)
# Optional full rebuild: mvn -o clean package
```

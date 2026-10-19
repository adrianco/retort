# Evaluation: rest-api-crud · agent=hermes-0222 language=java model=ThinkingCap-Qwen3.8-27B stack=tcap · rep 1

## Summary

- **Factors:** language=java, agent=hermes-0222, model=mlxlocal/bottlecapai--ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ, prompt=neutral, stack=tcap
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 32 passed / 0 failed / 0 skipped (32 effective) — from `test_coverage=1.0` in scores.json
- **Build:** pass — `test_coverage=1.0` ⇒ `mvn package` compiled + all tests ran (not re-run here)
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `BookApiHandler.java:52-56` → `BookStore.create`; test `createBookReturns201WithBookAndLocation` |
| R2 | GET /books lists all books | ✓ implemented | `BookApiHandler.java:47-50` → `BookStore.list(null)`; test `listBooksReturnsAllAndFiltersByAuthor` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `BookApiHandler.java:48 firstParam("author")`; `BookStore.java:62-66` WHERE author=?; test `listFiltersByAuthor` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `BookApiHandler.java:72-73` orElseThrow 404; test `getBookReturnsBookOr404` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `BookApiHandler.java:74-78` → `BookStore.update`; tests `updateBook*` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `BookApiHandler.java:79-84` → `BookStore.delete`, 204/404; test `deleteBookReturns204Then404` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `BookStore.java:22 DriverManager.getConnection("jdbc:sqlite:...")`, real table |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | `Json.write/error`; 200/201/204/400/404/405/500 across `BookApiHandler` |
| R9 | Input validation: title and author required | ✓ implemented | `BookValidation.java:validate` → 400; tests `createBookRejectsMissing*` |
| R10 | GET /health health-check | ✓ implemented | `BookApiHandler.java:41-45` → `{"status":"ok"}`; test `healthEndpointReturnsOk` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — Setup (`mvn package`), Run (`java -jar`), config table |
| R12 | At least 3 unit/integration tests | ✓ implemented | 32 `@Test` across 3 files; `test_coverage=1.0` |

## Build & Test

Build/test not re-run — stored scores authoritative (per evaluate-run skill).

```text
scores.json
test_coverage = 1.0   # mvn package: compiled + all tests passed
code_quality  = 1.0
defect_rate   = 1.0
maintainability = 0.888
idiomatic     = 0.72
```

```text
@Test count: BookApiIntegrationTest=14, BookStoreTest=9, BookValidationTest=9  (32 total)
skip scan (@Disabled/@Ignore/assumeTrue): none found
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, .java) | 880 |
| Files (excl. logs/session artifacts) | 20 |
| Dependencies (pom artifactIds) | 7 |
| Tests total | 32 |
| Tests effective | 32 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

All 3 findings are info-level (no deductions):

1. [info] Error handling beyond spec: 405 + `Allow` header, 404 for unknown paths, 500 fallback
2. [info] POST returns `Location` header; SQLite runs in WAL mode
3. [info] PUT does a partial merge of optional fields rather than a full replace (documented, tested)

## Reproduce

```bash
cd "experiments/adrianco/experiment-89-thinkingcap-reach/rest-api-crud/runs/agent=hermes-0222_language=java_model=mlxlocal/bottlecapai--ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ_prompt=neutral_stack=tcap/rep1"
cat scores.json
grep -rc "@Test" src/test/java/com/example/books/*.java
# optional rebuild (slow, not needed — scores stored):
# mvn -q package
```

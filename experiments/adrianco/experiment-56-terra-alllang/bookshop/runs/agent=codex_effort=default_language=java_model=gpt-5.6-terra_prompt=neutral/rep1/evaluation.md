# Evaluation: agent=codex language=java model=gpt-5.6-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=java, model=gpt-5.6-terra, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — `test_coverage=1.0` from `scores.json`
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** summary skill unavailable (see note below)
- **Findings:** 0 items in `findings.jsonl`

A tidy, idiomatic Java 21 implementation using Javalin + JDBC SQLite. All mechanical
scores from `scores.json`: `test_coverage=1.0`, `code_quality=1.0`, `defect_rate=1.0`,
`maintainability=0.82`, `idiomatic=0.75`. The only entry in `_agent_stderr.log` is a
sandbox-rejected `rm -rf` command (safety guard); the agent recovered with a safer build
path — no impact on the delivered code.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `BookApplication.java:15-18`, `BookRepository.create` (`BookRepository.java:26-36`) |
| R2 | GET /books lists all books | ✓ implemented | `BookApplication.java:19`, `BookRepository.findAll` (`:38-48`) |
| R3 | GET /books ?author= filter | ✓ implemented | `BookRepository.java:39` `WHERE author = ?`; test `filtersBooksByExactAuthor` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `BookApplication.java:20-21`, `notFound` on empty (`:48`) |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `BookApplication.java:22-26`, `BookRepository.update` (`:59-66`) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `BookApplication.java:27-30`, `BookRepository.delete` (`:68-73`) → 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `BookRepository.java:11-24` JDBC `jdbc:sqlite:` + `CREATE TABLE` |
| R8 | JSON responses, appropriate status codes | ✓ implemented | `ctx.json(...)` + `HttpStatus.CREATED/NO_CONTENT/NOT_FOUND/BAD_REQUEST` |
| R9 | Validation: title and author required | ✓ implemented | `BookApplication.valid` (`:38-42`) → 400; test `rejectsMissingRequiredFields` |
| R10 | GET /health health check | ✓ implemented | `BookApplication.java:14` returns `{"status":"ok"}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — run, endpoints, curl example |
| R12 | At least 3 unit/integration tests | ✓ implemented | 4 `@Test` methods in `BookApplicationTest.java` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per evaluate-run skill):

```text
test_coverage = 1.0   → build + all tests passed
code_quality  = 1.0   → lint/quality clean
defect_rate   = 1.0   → build+test succeeded
```

Tests (4, all effective, none skipped): `createsAndRetrievesBook`,
`filtersBooksByExactAuthor`, `updatesAndDeletesBook`, `rejectsMissingRequiredFields`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, incl. test) | 204 |
| Files (src) | 5 |
| Dependencies (pom `<dependency>`) | 3 |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

None. All 12 pinned requirements implemented, tests pass, no skipped/disabled tests,
no lint issues. `findings.jsonl` is empty → `penalty_score = 1.0`.

## Reproduce

```bash
cd "experiments/adrianco/experiment-56-terra-alllang/bookshop/runs/agent=codex_effort=default_language=java_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json                                    # mechanical scores (no re-run)
grep -rE "@Disabled|assumeTrue|@Ignore" src        # skip detection → 0
grep -rc "@Test" src/test                          # test count → 4
find src -name '*.java' | xargs wc -l | tail -1    # LOC → 204
```

# Evaluation: java · hermes-local · Qwen3-Coder-Next-4bit · prompt=repair · stack=m80 · rep 1

> **Second opinion / re-check.** A first evaluation scored `requirement_coverage=0.9167`
> but recorded no specific requirement findings. I independently re-verified all 12
> requirements against the source. **Conclusion: the 0.9167 number stands.** All 12
> requirements are *functionally present* in the code; the single non-full requirement is
> **R10** — the health endpoint is served at `/api/books/health`, not the spec's `/health`.
> The first evaluator was not wrong on the score, only silent on the reason; this report
> supplies the evidence.

## Summary

- **Factors:** language=java, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, agent=hermes-local, prompt=repair, stack=m80
- **Status:** ok (build + tests executed; 5/24 tests fail — not a hard fail since test_coverage > 0)
- **Requirements:** 11/12 implemented, 1 partial (R10), 0 missing → **requirement_coverage = 0.9167**
- **Tests:** 19 passed / 5 failed / 0 skipped (24 effective) — from `scores.json` test_coverage=0.7917
- **Build:** pass — from `scores.json` defect_rate=1.0 (not re-run)
- **Lint/quality:** pass — `scores.json` code_quality=1.0, maintainability=0.9617
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 1 high, 2 medium, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST creates a book (4 fields) | ✓ implemented | `controller/BookController.java:31` createBook → `service/BookService.java:22` persists |
| R2 | GET lists all books | ✓ implemented | `BookController.java:46` getAllBooks → findAll |
| R3 | GET ?author= filter | ✓ implemented | `BookController.java:47-52` @RequestParam → `BookService.findByAuthor` → `BookRepository.findByAuthor` |
| R4 | GET /{id}, 404 if absent | ✓ implemented | `BookController.java:59-63` throws ResourceNotFoundException → `handler/GlobalExceptionHandler.java:18` → 404 |
| R5 | PUT updates a book | ✓ implemented | `BookController.java:66-72` → `BookService.updateBook:37` |
| R6 | DELETE removes a book | ✓ implemented | `BookController.java:75-78` returns 204; `BookService.deleteBook:52` → 404 if missing |
| R7 | SQLite / embedded DB | ✓ implemented | `main/resources/application.properties:2` `jdbc:sqlite:books.db`; pom `sqlite-jdbc` + `SQLiteDialect` |
| R8 | JSON + HTTP status codes | ✓ implemented | 201 (created, `BookController.java:38`), 200, 404, 400 (`GlobalExceptionHandler`) |
| R9 | Validation: title & author required | ✓ implemented | `dto/BookRequest.java:7,11` @NotBlank + `@Valid` (`BookController.java:32`) → 400 via handler:29 |
| R10 | GET /health | ~ **partial** | `BookController.java:78` `@GetMapping("/health")` under base `/api/books` (line 20) ⇒ resolves to `/api/books/health`, **not** `/health`; returns "OK"/200 but a spec client hitting `/health` gets 404 |
| R11 | README with setup/run | ✓ implemented | `README.md` — Setup, Running, Testing, API usage sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 24 tests across 3 classes; test_coverage=0.7917 > 0 |

**Enhancements beyond spec (not deductions):** dedicated `GlobalExceptionHandler` (the core
repair — fixes the pre-repair 500→404), `BookRequest`/`BookResponse` DTO separation,
`@Size` length constraints and dedicated validation unit tests.

## Build & Test

Mechanical scores read from `scores.json` (per evaluate-run: do **not** re-run the JVM
toolchain when stored scores exist):

```text
code_quality      = 1.0
token_efficiency  = 0.00254
test_coverage     = 0.7917   => 19/24 tests pass, 5 fail
defect_rate       = 1.0      => build + tests executed
maintainability   = 0.9617
idiomatic         = 0.70
```

**The 5 failing tests are test-design flaws, not API defects** (agent admits this in
`_agent_stdout.log`):
- 4× `BookControllerIntegrationTest` assert absolute ids / `Location: /api/books/1`
  (lines 51, 143, 178, 199) but the shared H2 `IDENTITY` sequence is not reset by
  `@Transactional` rollback, so created rows get ids > 1.
- 1× `BookRepositoryTest.testBookValidationConstraints` (line 151) expects
  `ConstraintViolationException` from `save()`, but validation fires on flush/commit, which
  the transactional test rolls back.

The repair task's stated goal was "all tests run and pass"; that goal was **not** met
(19/24). The underlying REST API, however, conforms to the spec.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main, Java) | 354 |
| Lines of code (test, Java) | 501 |
| Files (src tree) | 16 |
| Tests total | 24 |
| Tests effective (passed+failed) | 24 |
| Skip ratio | 0% |
| Build | pass (defect_rate=1.0) |

## Findings

Top items (full list in `findings.jsonl`):

1. [high] `test-fail-idseq` — 4 controller tests fail: H2 IDENTITY sequence not reset across `@Transactional` rollback (hard-coded id=1).
2. [medium] `R10` — health endpoint at `/api/books/health`, not spec `/health`.
3. [medium] `test-fail-validation` — `testBookValidationConstraints` expects `save()` to throw; validation is deferred to flush and rolled back.
4. [info] `api-prefix` — routes under `/api/books` rather than spec `/books` (behaviorally equivalent CRUD; noted for cross-run comparison).
5. [info] `toolchain-note` — scores read from `scores.json`, JVM not re-run.

## Reproduce

```bash
cd experiments/adrianco/experiment-41-repair-80b-fullctx/bookshop/runs/agent=hermes-local_language=java_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=repair_stack=m80/rep1
cat scores.json                                    # mechanical scores (not re-run)
sed -n '19,80p' src/main/java/com/bookapi/controller/BookController.java   # /api/books base + /health mapping
grep -rn "health" src/main src/test                # R10 path evidence
grep -rEc "@Test" src/test --include='*.java'      # test count
```

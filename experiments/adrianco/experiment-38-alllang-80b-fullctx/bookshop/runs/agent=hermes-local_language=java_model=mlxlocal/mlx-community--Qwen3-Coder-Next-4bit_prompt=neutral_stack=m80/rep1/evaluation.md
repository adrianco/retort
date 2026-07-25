# Evaluation: java · hermes-local · Qwen3-Coder-Next-4bit (m80) · rep 1

## Summary

- **Factors:** language=java, agent=hermes-local, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, prompt=neutral, stack=m80
- **Status:** ok (functional, one real defect: not-found → 500)
- **Requirements:** 9/12 implemented, 3 partial (R4, R8, R10), 0 missing → **requirement_coverage = 0.75**
- **Tests:** ~24 tests, 3 failing (not-found cases), 0 skipped — test_coverage=0.6667 (scores.json)
- **Build:** pass (defect_rate=1.0 ⇒ build+test executed)
- **Lint:** code_quality=1.0 (one unused import noted)
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (2 high, 1 medium, 2 low)

## Second-opinion verdict on the prior evaluation

The first evaluation scored **requirement_coverage=0.5833 (7/12)** and claimed R4/R5/R6/R8
were all broken by the missing 404 mapping.

**The R4 core claim is CONFIRMED.** I checked directly:
- `src/main/java/com/bookapi/service/ResourceNotFoundException.java:3` — a plain
  `RuntimeException`, **no `@ResponseStatus`**.
- `grep -rn '@ControllerAdvice|@RestControllerAdvice|@ExceptionHandler'` over `src/main`
  returns **nothing** — no global handler exists.
- `BookController.java:9` imports `HttpStatus` but **never uses it** (the intended-but-omitted
  404 wiring).
- The controller/service throw `ResourceNotFoundException` on missing ids
  (`BookController.java:60`, `BookService.java:41`, `BookService.java:53`), so Spring's default
  handler returns **HTTP 500**, not 404.
- The not-found tests (`BookControllerTest` `testGetBookByIdNotFound:158`,
  `testUpdateBookNotFound:189`, `testDeleteBookNotFound:222`) `andExpect(isNotFound())` and
  therefore **fail** — matching `test_coverage=0.6667`.

**But the first evaluator over-reached** by failing R5 and R6 for "404 if absent". This
experiment's *pinned* `REQUIREMENTS.json` does **not** impose 404 on R5/R6 — their
`how_to_verify` is only "modifies an existing book" (R5) and "removes a book" (R6). Both
happy-path update (`BookController.java:64-70`, `BookService.updateBook:39`) and delete
(`BookController.java:72-76`, `BookService.deleteBook:51`) are correctly implemented. Only
**R4** explicitly requires "404 if absent", and **R8** requires correct status codes — those
two are the requirements the 404 defect actually breaks. So the corrected count is **9/12,
not 7/12**.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST creates a book | ✓ implemented | `BookController.createBook:28`, `BookService.createBook:21` → 201 |
| R2 | GET lists all books | ✓ implemented | `BookController.getAllBooks:43`, `BookRepository.findAll` |
| R3 | `?author=` filter | ✓ implemented | `getAllBooks:44` `@RequestParam author` → `BookRepository.findByAuthor` |
| R4 | GET by id (404 if absent) | ~ partial | happy path `getBookById:58` ok; **not-found returns 500** — `ResourceNotFoundException.java:3` unmapped |
| R5 | PUT updates a book | ✓ implemented | `updateBook:64`, `BookService.updateBook:39` (how_to_verify has no 404 clause) |
| R6 | DELETE deletes a book | ✓ implemented | `deleteBook:72`, `BookService.deleteBook:51` |
| R7 | SQLite / embedded DB | ✓ implemented | `application.properties` `jdbc:sqlite:books.db`, `sqlite-jdbc` in pom, `SQLiteDialect` |
| R8 | JSON + correct status codes | ~ partial | 201/200/400 correct; **404 case returns 500** (same root cause as R4) |
| R9 | Validation: title & author required | ✓ implemented | `BookRequest.java` `@NotBlank` + `@Valid` in controller → 400 |
| R10 | GET /health | ~ partial | endpoint exists but at **`/api/books/health`** (`getBookById` mapping nested under `/api/books`), not `/health` |
| R11 | README setup/run | ✓ implemented | `README.md` documents mvn build/run, port 8080 |
| R12 | ≥ 3 tests | ✓ implemented | ~24 `@Test` across 3 test classes; test_coverage=0.6667 > 0 |

## Build & Test

From `scores.json` (mechanical scores; not re-run per skill step 2):

```text
test_coverage = 0.6667   # build+tests ran; 3 not-found tests fail
defect_rate   = 1.0      # build+test executed
code_quality  = 1.0
maintainability = 0.959
idiomatic     = 0.7
```

Failing tests (contract is correct, implementation is not): `testGetBookByIdNotFound`,
`testUpdateBookNotFound`, `testDeleteBookNotFound` — all expect 404, receive 500.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (java, src) | 808 |
| Java files | 12 (7 main, 5 test) |
| Tests total | ~24 |
| Tests effective | ~24 (0 skipped) |
| Skip ratio | 0% |
| Requirement coverage | 0.75 (9/12) |

## Findings

Full list in `findings.jsonl`:

1. [high] R4 — not-found returns HTTP 500, not 404 (`ResourceNotFoundException.java:3` unmapped)
2. [high] test_failure — 3 not-found tests fail (expect 404, get 500)
3. [medium] R8 — 404 status code wrong (same root cause)
4. [low] R10 — health endpoint at `/api/books/health`, not `/health`
5. [low] unused import `HttpStatus` (`BookController.java:9`)

## Reproduce

```bash
cd experiments/adrianco/experiment-38-alllang-80b-fullctx/bookshop/runs/agent=hermes-local_language=java_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep1
cat src/main/java/com/bookapi/service/ResourceNotFoundException.java   # plain RuntimeException, no @ResponseStatus
grep -rn "ControllerAdvice\|ExceptionHandler\|ResponseStatus" --include='*.java' src/main  # none
grep -n "isNotFound" src/test/java/com/bookapi/controller/BookControllerTest.java
cat scores.json   # test_coverage=0.6667
```

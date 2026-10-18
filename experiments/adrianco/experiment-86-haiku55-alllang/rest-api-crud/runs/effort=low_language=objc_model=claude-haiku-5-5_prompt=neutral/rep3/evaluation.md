# Evaluation: rest-api-crud effort=low language=objc model=claude-haiku-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=objc, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 test functions (dozens of CHECK assertions) passed / 0 failed / 0 skipped (8 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + tests succeeded)
- **Lint:** pass — code_quality=1.0 from scores.json, 0 warnings
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/BookAPI.m:90 createBook:`, `src/BookStore.m:98 insertBook:` → 201 + Location |
| R2 | GET /books lists all | ✓ implemented | `src/BookAPI.m:107 listBooks:`, `src/BookStore.m:130` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/BookAPI.m:108`, `src/BookStore.m:129` (COLLATE NOCASE) |
| R4 | GET /books/{id} single | ✓ implemented | `src/BookAPI.m:120 getBook:`, `src/BookStore.m:112` (404 if absent) |
| R5 | PUT /books/{id} update | ✓ implemented | `src/BookAPI.m:127 updateBook:request:`, `src/BookStore.m:150` (404 if absent) |
| R6 | DELETE /books/{id} delete | ✓ implemented | `src/BookAPI.m:142 deleteBook:`, `src/BookStore.m:169` → 204 |
| R7 | SQLite / embedded DB | ✓ implemented | `src/BookStore.m:1 #import <sqlite3.h>`, `kSchema` CREATE TABLE books |
| R8 | JSON responses + status codes | ✓ implemented | `src/HTTP.h:24 jsonResponse:object:`; 201/200/204/400/404/405/503 used throughout `BookAPI.m` |
| R9 | Validation: title+author required | ✓ implemented | `src/Book.m:31-41` rejects blank title/author → 400 |
| R10 | GET /health | ✓ implemented | `src/BookAPI.m:81 health` → 200 `{status:ok}` / 503 |
| R11 | README with setup/run | ✓ implemented | `README.md` (100 lines): Requirements, Build, Run, API, env vars |
| R12 | ≥3 unit/integration tests | ✓ implemented | `tests/BookServiceTests.m` — 8 test functions; test_coverage=1.0 |

No `prompt` factor beyond `neutral` (the neutral prompt adds no extra checkable instructions), so there are no `P*` requirements.

## Build & Test

Scores read from `scores.json` (inline gate output); build/test/lint were **not** re-run per the evaluate-run skill.

```text
scores.json:
  test_coverage = 1.0   ⇒ build succeeded + all tests passed
  defect_rate   = 1.0   ⇒ build+test success
  code_quality  = 1.0   ⇒ lint clean
  maintainability = 0.792
  idiomatic     = 0.82
  token_efficiency = 0.028
```

Build: `make` → `clang -fobjc-arc ... -framework Foundation -lsqlite3` (compiled artifact present at `bin/bookservice`).
Test: `make test` → custom harness in `tests/BookServiceTests.m`; `_agent_stderr.log` is empty (0 bytes), no failures recorded. Skip scan over `src/` and `tests/` found 0 skipped/disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, src/) | 902 |
| Lines (tests) | 311 |
| Lines (README + Makefile) | 126 |
| Files (source, non-artifact) | 13 (6 `.m`, 5 `.h` in src + main.m + 1 test) |
| Dependencies | 0 third-party (Foundation + system libsqlite3 only) |
| Tests total | 8 functions |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build | pass |

## Findings

No defects. 2 info-level enhancements (full list in `findings.jsonl`):

1. [info] E1 — Router is socket-independent and tested both directly and over a real loopback socket (8 test functions, well beyond the 3-test minimum).
2. [info] E2 — Validation/HTTP semantics exceed spec: 405 + `Allow` header, 400 for malformed id, year range 0–9999, case-insensitive author filter.

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=objc_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json                                   # stored build/test/lint scores (not re-run)
cat ../../../REQUIREMENTS.json                    # pinned 12-requirement checklist
grep -rnE "skip|Skip|DISABLED|#if 0" src tests    # skip scan (0 hits)
# Optional full rebuild (not required by evaluate-run):
#   make && make test
```

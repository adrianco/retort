# Evaluation: effort=high_language=python_model=claude-sonnet-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-sonnet-5-5, prompt=neutral, effort=high
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective) — 8 functions, one parametrized ×7
- **Build:** pass — from `test_coverage=0.94`, `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.7889` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Prompt factor `neutral` (`prompts/neutral.md`) prescribes no methodology and only asks for tests demonstrating the requirements — satisfied; it adds no separate `P*` checklist items.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:157 create_book`, dispatch `app.py:118`; test `test_app.py:47` |
| R2 | GET /books lists all | ✓ implemented | `app.py:170 list_books`; test `test_app.py:79` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:173-177` COLLATE NOCASE; test `test_app.py:80-82` |
| R4 | GET /books/{id} + 404 | ✓ implemented | `app.py:185 get_book`, 404 `app.py:192`; test `test_app.py:51,103` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:195 update_book`, 404 `app.py:205`; test `test_app.py:85-91` |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:210 delete_book`, 404 `app.py:216`; test `test_app.py:94-98` |
| R7 | SQLite persistence | ✓ implemented | `app.py:33 init_db`, `sqlite3` throughout |
| R8 | JSON + correct status codes | ✓ implemented | `app.py:99-105` JSON wrapper; STATUS_TEXT `app.py:13-22` |
| R9 | Validation: title & author required | ✓ implemented | `app.py:47-71 validate_book`; test `test_app.py:55-67` (returns 422, see findings) |
| R10 | GET /health | ✓ implemented | `app.py:112-114`; test `test_app.py:41` |
| R11 | README with setup/run | ✓ implemented | `README.md` Setup/Run/Test/Endpoints sections |
| R12 | ≥3 tests | ✓ implemented | `test_app.py` 8 functions / 14 cases; `test_coverage=0.94` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill Step 2):

```text
test_coverage = 0.94   # tests executed and passed; 94% line coverage
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.7889 # lint/quality
maintainability = 0.9116
idiomatic     = 0.70
token_efficiency = 0.0495
```

Skip scan (`grep -E "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py`): 0 matches.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 356 (app.py 250 + test_app.py 106) |
| Files (non-artifact) | 5 tracked (app.py, test_app.py, README.md, requirements.txt, .gitignore) |
| Dependencies | 1 (pytest, test-only) |
| Tests total | 14 (8 functions, 1 parametrized ×7) |
| Tests effective | 14 |
| Skip ratio | 0% |
| Build duration | n/a (scores read from archive) |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level, no deductions:

1. [info] R9 — missing title/author returns 422 (Unprocessable Entity), not the 400 the pinned checklist parenthetically suggests. Semantically correct; 400 is reserved for malformed JSON. Requirement fully satisfied.
2. [info] Zero third-party runtime dependencies — stdlib WSGI + sqlite3.
3. [info] Error taxonomy beyond spec (405 method-not-allowed, 413 payload-too-large), tested.

## Reproduce

```bash
cd runs/effort=high_language=python_model=claude-sonnet-5-5_prompt=neutral/rep1
cat scores.json                                   # stored build/test/lint scores
grep -cE "^def test_" test_app.py                 # test function count
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py   # skip scan
# (build/tests NOT re-run — scores read from scores.json per evaluate-run Step 2)
```

# Evaluation: language=python model=opus-4.8 prompt=bdd · rep 1

## Summary

- **Factors:** language=python, model=opus-4.8, prompt=bdd (framework chosen by agent: FastAPI)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (+ 4/4 BDD prompt instructions followed)
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective)
- **Build:** pass — test_coverage=0.99 from scores.json (build + tests ran)
- **Lint:** pass — code_quality=0.83 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.py:49-51` → `db.py:41-47`; test `test_given_valid_book_when_create_then_returns_201_with_id` |
| R2 | GET /books lists all books | ✓ implemented | `main.py:53-55`; test `..._list_without_filter_then_returns_all` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `main.py:54`, `db.py:51-52`; test `..._list_filtered_then_returns_only_matches` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `main.py:57-62`; tests `..._get_by_id_then_returns_that_book`, `..._returns_404` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.py:64-71`, `db.py:63-71`; tests `..._update_then_fields_are_changed`, `..._update_then_returns_404` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.py:73-77`, `db.py:73-76`; tests `..._delete_then_it_is_gone`, `..._delete_then_returns_404` |
| R7 | Data stored in SQLite | ✓ implemented | `db.py:9-30` real `sqlite3` connection + schema |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/404/204 via route decorators + `HTTPException`; 422 for validation |
| R9 | Validation: title and author required | ✓ implemented | `main.py:21-24` `Field(..., min_length=1)`; tests assert 422 on missing/empty (info: 422 not 400, see findings) |
| R10 | GET /health endpoint | ✓ implemented | `main.py:45-47`; test `..._get_health_then_status_is_ok` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — setup, run, curl examples, status-code table |
| R12 | At least 3 unit/integration tests | ✓ implemented | 12 tests in `test_books.py`, all pass (test_coverage=0.99) |

### BDD prompt instructions (prompt=bdd)

| ID | Instruction | Status | Evidence |
|----|----|----|----|
| P1 | Given/When/Then sections | ✓ implemented | Every test has Given/When/Then comments (`test_books.py:29-138`) |
| P2 | Names after observable behaviours | ✓ implemented | e.g. `test_given_missing_title_when_create_then_returns_422` |
| P3 | One assertion per scenario where practical | ✓ implemented | Most tests assert a single behaviour; create/update assert status + one field |
| P4 | Descriptive `given_..._when_..._then_...` names | ✓ implemented | All 12 test names follow the pattern |

## Build & Test

Mechanical scores read from `scores.json` (not re-run, per skill guidance):

```text
test_coverage: 0.99   (build + tests executed; all pass)
code_quality:  0.83   (lint/quality)
defect_rate:   1.0    (build + test succeeded)
token_efficiency: 1.0
maintainability: 0.27  (heuristic; see findings info note)
idiomatic:       0.42  (heuristic)
```

Agent's own run log (`_agent_stdout.log`): "All 12 pass." — consistent with test_coverage=0.99.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 167 (main.py 88, db.py 79) |
| Lines of test code | 146 |
| Files (excl. .venv/artifacts) | ~9 source/config |
| Dependencies | 4 (fastapi, uvicorn, httpx, pytest) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build/test | pass (test_coverage=0.99) |

## Findings

All findings are informational — no defects (full list in `findings.jsonl`):

1. [info] R9 validation returns 422 (FastAPI standard) rather than 400 — satisfies the "rejected" intent, no change needed.
2. [info] `books.db` SQLite artifact committed into the archive — harmless, gitignored and regenerated on startup.
3. [info] Heuristic maintainability (0.27) / idiomatic (0.42) scores are low despite objectively clean, small, documented code — scorer artifact on tiny codebases.

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=python_model=opus-4.8_prompt=bdd/rep1
# Mechanical scores (do not re-run toolchain):
cat scores.json
# Skips / test count:
grep -cE "^def test_" test_books.py            # 12
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_books.py  # 0
# To run tests fresh (optional):
pip install -r requirements.txt && pytest
```

# Evaluation: agent=hermes-local language=python prompt=repair · rep 2

## Summary

- **Factors:** language=python, agent=hermes-local (Qwen3.6-35B-A3B), framework=flask, prompt=repair
- **Status:** ok — repair succeeded (previous attempt's two defects fixed)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective)
- **Build:** pass — `defect_rate=1.0` from scores.json (build+test gate)
- **Lint:** pass — `code_quality=0.833` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

This was a REPAIR-prompt run. `FEEDBACK.md` flagged two failures in the prior attempt: (1) build/tests did not fully pass, (2) no README.md. Both are resolved — tests pass 15/15, README.md is present with setup/run/API docs.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:44` create_book_endpoint → `models.py:66` create_book |
| R2 | GET /books lists all | ✓ implemented | `app.py:69` list_books_endpoint → `models.py:115` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:72` reads args; `models.py:125` LOWER(author)=LOWER(?) |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `app.py:77-83` returns 404 when None |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:86` → `models.py:138` update_book |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:115` → `models.py:190` delete_book |
| R7 | SQLite persistence | ✓ implemented | `models.py:3,25` sqlite3.connect; books table `models.py:52` |
| R8 | JSON responses + status codes | ✓ implemented | jsonify throughout; 201/200/404/400 (`app.py:66,74,82,57`) |
| R9 | Validation: title & author required | ✓ implemented | `app.py:56-59` (400); `models.py:81-84` ValueError |
| R10 | GET /health | ✓ implemented | `app.py:38-41` returns {"status":"ok"},200 |
| R11 | README.md setup/run | ✓ implemented | `README.md` — setup, run, endpoints, curl examples |
| R12 | ≥3 tests that run | ✓ implemented | `test_app.py` — 15 tests, `test_coverage=0.9` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
defect_rate      = 1.0    # build + tests pass
test_coverage    = 0.9    # 90% line coverage, 15 tests, 0 skips
code_quality     = 0.833
maintainability  = 0.902
idiomatic        = 0.7
token_efficiency = 0.022
```

Root-cause fix documented in `_agent_stdout.log`: nested-connection bug where `create_book`/`update_book` called `get_book_by_id` (a *new* connection) before commit, so the SELECT saw no rows. Fixed by inlining `conn.execute(...).fetchone()` on the same connection (`models.py:92`, `models.py:183`).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 553 (app 128, models 216, tests 209) |
| Files | 16 |
| Dependencies | 2 (flask, pytest) |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| Agent API calls / tokens | 14 calls / 391,196 total tokens |

## Findings

Full list in `findings.jsonl` (nothing at medium+):

1. [low] Dead/broken `get_db_path` helper in `app.py:15-17` — unused, would raise AttributeError if its guarded branch executed.
2. [info] Agent file-mutation verifier warned `models.py` unmodified this turn (`_agent_stdout.log:26`), but the fix is present in the archived file and tests pass.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-21-repair-lcm/bookshop/runs/agent=hermes-local_language=python_prompt=repair/rep2
cat scores.json                                  # stored build/test/quality scores
grep -rEn "def test_" test_app.py | wc -l        # 15 tests
grep -rEn "pytest\.skip|xfail" . --include="*.py" | wc -l   # 0 skips
# optional re-run: pip install -r requirements.txt && pytest test_app.py -v
```

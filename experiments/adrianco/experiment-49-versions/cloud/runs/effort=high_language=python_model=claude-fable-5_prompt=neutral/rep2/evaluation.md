# Evaluation: effort=high_language=python_model=claude-fable-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-fable-5, prompt=neutral, effort=high
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 12 tests (with a 7-case parametrize → 19 effective cases), 0 failed, 0 skipped
- **Build:** pass — `test_coverage=1.0`-gate passed (coverage 0.97 from scores.json)
- **Lint:** pass — `code_quality=0.79`, `idiomatic=0.74` from scores.json
- **Architecture:** single-module Flask app-factory (`app.py`) + `test_app.py`; `run-summary` skill unavailable in this session
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

Denominator fixed by the experiment's pinned `REQUIREMENTS.json` (12 entries).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:88` `create_book` inserts title/author/year/isbn |
| R2 | GET /books lists all | ✓ implemented | `app.py:106` `list_books` returns collection |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:110-113` filters by `author` param |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:118` `get_book`, 404 at `:122` |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:125` `update_book`, partial updates |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:150` `delete_book`, 204/404 |
| R7 | SQLite persistence | ✓ implemented | `app.py:10-26` schema + `sqlite3.connect` |
| R8 | JSON + correct status codes | ✓ implemented | `jsonify` throughout; 201/200/404/400/204 |
| R9 | title & author required | ✓ implemented | `app.py:56-64` `validate_payload` rejects missing/empty |
| R10 | GET /health | ✓ implemented | `app.py:84` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, API table, examples |
| R12 | ≥3 tests | ✓ implemented | `test_app.py` 12 test functions; `test_coverage=0.97` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill policy):

```text
test_coverage = 0.97   # build + tests executed and passed (coverage 97%)
defect_rate   = 1.0    # build+test succeeded
maintainability = 1.0
code_quality  = 0.7889
idiomatic     = 0.74
```

Skip scan (`grep pytest.skip|mark.skip|xfail`): 0 skips — all tests effective.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py, non-blank) | 136 |
| Lines of code (test_app.py, non-blank) | 96 |
| Files (excl. __pycache__/.coverage) | 11 |
| Dependencies | 2 (flask, pytest) |
| Tests total | 12 functions (19 effective incl. parametrize) |
| Tests skipped | 0 |
| Skip ratio | 0% |
| Coverage | 97% |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] code_quality 0.79 / idiomatic 0.74 — minor style deductions, no functional impact
2. [info] Validation exceeds spec — type checks on year/isbn + non-JSON body rejection
3. [info] PUT partial updates via a parameterized, allow-listed dynamic UPDATE (no injection risk)

No critical/high/medium findings. All 12 pinned requirements implemented and tested.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-49-versions/cloud/runs/effort=high_language=python_model=claude-fable-5_prompt=neutral/rep2
cat scores.json                                   # mechanical scores (not re-run)
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l   # 0
python3 -m pytest -v                              # optional: 12 tests pass
```

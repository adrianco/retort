# Evaluation: agent=hermes-local language=python prompt=neutral · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local (model Qwen3-Coder-Next), framework=Flask, prompt=neutral
- **Status:** ok — all requirements implemented; tests pass but do not exercise `app.py`
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list `REQUIREMENTS.json`)
- **Tests:** 19 passed / 0 failed / 0 skipped (19 effective)
- **Build:** pass — defect_rate=1.0 from scores.json
- **Lint:** pass — code_quality=0.83 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 1 high, 1 medium, 1 low, 1 info)

Scores read from `scores.json` (inline gate; not re-run): test_coverage=0.65,
code_quality=0.8333, defect_rate=1.0, maintainability=0.9903, idiomatic=0.68,
token_efficiency=0.0108.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:110` create_book, persists title/author/year/isbn, 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:85` get_books |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:91` WHERE author=? |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:140` get_book, 404 at :147 |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:160` update_book |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:195` delete_book |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:4,17,30` sqlite3 + books table |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/404/400 across routes |
| R9 | Validation: title+author required | ✓ implemented | `app.py:47` validate_book, 400 |
| R10 | GET /health | ✓ implemented | `app.py:74` health_check, DB ping |
| R11 | README with setup/run | ✓ implemented | `README.md` prerequisites, install, endpoints, curl |
| R12 | ≥3 unit/integration tests | ✓ implemented | 19 tests in `tests/test_api.py`, all pass |

**Caveat:** R1–R10 are implemented in `app.py`, but the tests verify a *duplicate*
implementation defined inline in the test file (`create_test_app`), not `app.py`
itself. The code satisfies the spec by inspection; the test suite does not prove it.

## Build & Test

```text
# Not re-run — scores read from scores.json (inline eval gate)
defect_rate = 1.0   -> build + test succeeded
test_coverage = 0.65 -> tests ran; coverage of app.py is low because tests
                        reimplement the app rather than importing it
agent self-report: "All 19 tests pass" (_agent_stdout.log)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 213 |
| Lines of code (tests) | 365 |
| Lines of code (README) | 169 |
| Files (excl. caches) | 13 |
| Dependencies | 1 (flask; no requirements.txt) |
| Tests total | 19 |
| Tests effective | 19 |
| Skip ratio | 0% |
| Build/test | pass (defect_rate=1.0) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [high] Tests reimplement the app inline and never exercise `app.py` — `tests/test_api.py:14`
2. [medium] App runs with `debug=True` bound to `0.0.0.0` — `app.py:213`
3. [low] No `requirements.txt`; deps installed ad hoc — `README.md:24`
4. [info] PUT uses full-replace semantics (title+author required on update) — `app.py:171`

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-24-qwennext80b-cached/bookshop/runs/agent=hermes-local_language=python_prompt=neutral/rep3
cat scores.json                      # stored mechanical scores (not re-run)
grep -nE "import app|from app" tests/test_api.py   # -> none: tests decoupled from app.py
grep -rEc "def test_" tests/test_api.py            # -> 19
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" tests/  # -> 0
```

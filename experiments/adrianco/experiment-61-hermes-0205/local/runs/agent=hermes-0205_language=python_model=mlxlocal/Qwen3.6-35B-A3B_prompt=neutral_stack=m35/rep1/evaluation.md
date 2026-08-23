# Evaluation: Qwen3.6-35B-A3B_prompt=neutral_stack=m35 · rep 1

## Summary

- **Factors:** language=python, agent=hermes-0205, model=mlxlocal/Qwen3.6-35B-A3B, prompt=neutral, stack=m35
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective) — `test_coverage=0.98` from `scores.json`
- **Build:** pass (Flask app imports cleanly; `defect_rate=1.0`, i.e. build+test succeeded)
- **Lint:** pass — `code_quality=0.8333` from `scores.json`
- **Architecture:** single-module Flask app (`app.py`) + pytest suite (`test_app.py`); `run-summary` skill unavailable in this session
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:54` `create_book`, INSERT at :75 |
| R2 | GET /books lists all | ✓ implemented | `app.py:86` `list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:92-96` `author LIKE ?` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:104` `get_book`, 404 at :109 |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:113` `update_book` |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:148` `delete_book` |
| R7 | SQLite / embedded DB | ✓ implemented | `app.py:13,27-40` sqlite3 + CREATE TABLE |
| R8 | JSON responses + status codes | ✓ implemented | `jsonify(...), 201/200/404/400` throughout |
| R9 | title & author required | ✓ implemented | `app.py:66-69` 400 on missing |
| R10 | GET /health | ✓ implemented | `app.py:48-51` returns `{"status":"healthy"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` (setup, run, endpoints) |
| R12 | ≥3 tests | ✓ implemented | `test_app.py` — 14 tests, all pass |

## Build & Test

Scores read from `scores.json` (not re-run, per skill step 2):

```text
test_coverage = 0.98   # build + tests ran; suite passed
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.8333
```

Agent's own report (`_agent_stdout.log`): "Test results: 14/14 passed". No skips found via grep.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 176 (app.py) + 184 (test_app.py) = 360 |
| Files | app.py, test_app.py, README.md (+ generated books.db/.coverage) |
| Dependencies | flask, pytest (not pinned in a requirements file) |
| Tests total | 14 |
| Tests effective | 14 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] No requirements.txt / pinned Flask version — `README.md` says `pip install flask` but no dependency file exists
2. [info] PUT update re-validates title/author non-empty (defensive, beyond spec) — `app.py:129-132`

## Reproduce

```bash
cd "experiments/adrianco/experiment-61-hermes-0205/local/runs/agent=hermes-0205_language=python_model=mlxlocal/Qwen3.6-35B-A3B_prompt=neutral_stack=m35/rep1"
cat scores.json                               # stored mechanical scores
grep -rEc "pytest\.skip|xfail" test_app.py    # skip count (0)
grep -c "def test_" test_app.py               # 14
# to actually run: python -m venv venv && source venv/bin/activate && pip install flask pytest && pytest test_app.py -v
```

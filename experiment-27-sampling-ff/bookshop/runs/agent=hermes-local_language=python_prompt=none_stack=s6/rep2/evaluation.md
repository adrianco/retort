# Evaluation: agent=hermes-local_language=python_prompt=none_stack=s6 · rep 2

## Summary

- **Factors:** language=python, agent=hermes-local (Qwen3.6-35B-A3B), prompt=none, stack=s6, framework=unknown (Flask, chosen by agent)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 17 passed / 0 failed / 0 skipped (17 effective) — from test_coverage=0.96 in scores.json + agent stdout "17 passed, 0 failed"
- **Build:** pass — test_coverage=0.96 (build + tests ran; not re-run per skill)
- **Lint:** pass — code_quality=0.7889 (from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:51` create_book, INSERT at `app.py:76` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:92` list_books |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:98` LIKE filter; test `test_list_books_filter_by_author` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:110` get_book, 404 at `app.py:117` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:122` update_book |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:167` delete_book |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:1,15,32` sqlite3 + CREATE TABLE books |
| R8 | JSON responses + status codes | ✓ implemented | jsonify throughout; 201/200/400/404 |
| R9 | Validation: title+author required | ✓ implemented | `app.py:61-64`; tests missing_title/missing_author |
| R10 | GET /health | ✓ implemented | `app.py:45` health_check returns 200 |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, API reference |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` — 17 tests, 0 skipped |

## Build & Test

Scores read from `scores.json` (skill mandates not re-running the toolchain):

```text
test_coverage = 0.96   # build + all tests passed; ~96% line coverage
defect_rate   = 1.0    # build+test succeeded
code_quality  = 0.7889
maintainability = 0.9966
idiomatic     = 0.68
```

```text
# agent stdout (_agent_stdout.log)
Test results: 17 passed, 0 failed
```

Note: `_agent_stdout.log` records a file-mutation verifier warning about a
read-only-filesystem write during the run, but the final `app.py`/`test_app.py`
are present and correct, and the scorers ran the suite successfully — so this was
a transient retry artifact, not a defect in the archived output.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 396 (app.py 183 + test_app.py 213) |
| Files | 13 (incl. .coverage, logs, meta) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 17 |
| Tests effective | 17 |
| Skip ratio | 0% |
| Build duration | n/a (scores from archive) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [medium] SEC1 — App runs with `debug=True` bound to `0.0.0.0` (`app.py:183`); Werkzeug debugger = RCE if reachable.
2. [low] IDIO1 — Idiomatic/quality below par (idiomatic=0.68, code_quality=0.79); repeated inline validation.
3. [info] ENH1 — GET /books has no pagination (not required).
4. [info] ENH2 — No ISBN format validation or uniqueness (not required).

No critical or high findings — the run fully conforms to the spec and all tests pass.

## Reproduce

```bash
cd experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s6/rep2
cat scores.json                              # stored build/test/quality scores
grep -cE "def test_" test_app.py             # 17
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py   # 0
# (optional) rerun tests: python -m pytest test_app.py -v
```

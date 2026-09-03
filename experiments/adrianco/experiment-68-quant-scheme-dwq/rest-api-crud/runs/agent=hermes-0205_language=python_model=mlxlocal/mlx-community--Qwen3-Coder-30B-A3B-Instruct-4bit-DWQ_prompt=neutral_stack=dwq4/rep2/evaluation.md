# Evaluation: dwq4 · Qwen3-Coder-30B-4bit-DWQ · neutral · rep 2

## Summary

- **Factors:** language=python, agent=hermes-0205, model=mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ, prompt=neutral, stack=dwq4
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective)
- **Build:** pass — from `scores.json` (`defect_rate=1.0`, `test_coverage=0.75`)
- **Lint:** pass — `code_quality=0.83` from `scores.json`
- **Architecture:** single-module Flask app (`app.py`) over SQLite; see Metrics
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

Denominator is the pinned 12-item `REQUIREMENTS.json` (constant across all runs of this task).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:36` `create_book` inserts + returns 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:71` `get_books` returns collection |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:76-81` filters by `author` query param |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:89` returns book or 404 (`app.py:99`) |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:105` `update_book` updates + returns 200 |
| R6 | DELETE /books/{id} delete | ✓ implemented | `app.py:148` `delete_book` removes + returns 200 |
| R7 | Stored in SQLite | ✓ implemented | `app.py:8-22` `init_db` + `sqlite3` throughout |
| R8 | JSON + correct status codes | ✓ implemented | `jsonify` w/ 201/200/404/400/500 across routes |
| R9 | Validation: title+author required | ✓ implemented | `app.py:41-42` returns 400 when missing |
| R10 | GET /health | ✓ implemented | `app.py:31-33` returns `{status: healthy}` 200 |
| R11 | README with setup/run | ✓ implemented | `README.md` documents install + run + test |
| R12 | ≥3 tests | ✓ implemented | `test_app.py` has 10 `test_` methods; `test_coverage=0.75` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.75   # line coverage; tests executed and passed
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.83
maintainability = 0.90
idiomatic     = 0.58
```

Agent stdout confirms: "All 10 tests pass". No skipped/xfail markers found.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 526 (app.py 172, test_app.py 251, demo.py 103) |
| Files (excl. caches) | 3 `.py` + README + requirements |
| Dependencies | 1 (Flask) |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| Tokens (total) | 933,396 (in 31,287 / out 7,901); 33 API calls |

## Findings

Top items (full list in `findings.jsonl`) — no high+ severity findings:

1. [low] Tests share on-disk `books.db` rather than an isolated/in-memory DB (`test_app.py:24`)
2. [info] 10 tests implemented vs 3 required (enhancement)
3. [info] Extra `demo.py` script beyond spec (enhancement)

## Reproduce

```bash
cd "experiments/adrianco/experiment-68-quant-scheme-dwq/rest-api-crud/runs/agent=hermes-0205_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ_prompt=neutral_stack=dwq4/rep2"
cat scores.json                      # build/test/quality scores (not re-run)
grep -cE "def test_" test_app.py     # 10
grep -rE "skip|xfail" --include=*.py . | wc -l   # 0
```

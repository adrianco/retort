# Evaluation: agent=hermes-local · python · gpt-oss-20b-MXFP4-Q8 · neutral · gptoss · rep 5

> **Second-opinion re-check.** A first evaluation scored requirement_coverage=0.9167
> and flagged R12 (only 2 tests, spec needs >= 3) as not met. I re-verified that claim
> against the code before accepting it — see R12 below. **The first evaluator was correct.**

## Summary

- **Factors:** language=python, agent=hermes-local, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, prompt=neutral, stack=gptoss
- **Status:** ok (a repair task — `TASK.md` is a REPAIR prompt; prior `FEEDBACK.md` cited failed build + missing README, both now fixed)
- **Requirements:** 11/12 implemented, 1 partial (R12), 0 missing → **requirement_coverage = 0.9167**
- **Tests:** 2 passed / 0 failed / 0 skipped (2 effective) — **below the spec's 3-test floor**
- **Build:** pass — test_coverage=0.77 from `scores.json` (build + tests ran and passed; coverage 0.77 > 0)
- **Lint:** pass — code_quality=0.8333 from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 1 high)

## R12 re-verification (the disputed claim)

The first evaluator claimed only 2 test functions exist where the spec requires >= 3.
I checked:

- `grep -rn "def test_" tests/` → exactly two: `test_health` (`tests/test_api.py:7`) and
  `test_crud_book` (`tests/test_api.py:14`).
- `python3 -m pytest --collect-only -q tests/` → **2 collected items**.
- No other test files anywhere in the workspace (`find . -name "*test*"` finds only
  `tests/test_api.py`).

`test_crud_book` does exercise create/get/list-filter/update/delete/404 inside one
function, but pytest collects it as a single test. The deliverable and `REQUIREMENTS.json`
R12 ask for ">= 3 unit/integration tests" — the workspace has 2. **Confirmed not met.**
Classified `partial` (not `missing`): the tests that exist run and pass (test_coverage
0.77 > 0), so the how_to_verify's coverage clause is satisfied, but the count floor is not.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.py:36-53` `create_book`, persists all four fields, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `main.py:55-73` `list_books` returns the collection as JSON |
| R3 | GET /books ?author= filter | ✓ implemented | `main.py:57,60-61` filters `Book.author == author` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `main.py:75-88` `get_book`, `abort(404)` when absent |
| R5 | PUT /books/{id} update | ✓ implemented | `main.py:90-110` `update_book` sets provided fields, commits |
| R6 | DELETE /books/{id} | ✓ implemented | `main.py:112-122` `delete_book`, returns 204 |
| R7 | SQLite / embedded DB | ✓ implemented | `main.py:23-25` `create_engine("sqlite:///…books.db")`, `create_all` |
| R8 | JSON + proper status codes | ✓ implemented | `jsonify` throughout; 201/200/404/204/400 returned |
| R9 | Validation: title+author required | ✓ implemented | `main.py:39-40` `abort(400)` when title/author missing |
| R10 | GET /health | ✓ implemented | `main.py:31-33` returns `{"status":"ok"}` |
| R11 | README with setup+run | ✓ implemented | `README.md` — Setup, install, run, and test sections |
| R12 | >= 3 unit/integration tests | ~ partial | only 2 collected (`tests/test_api.py:7,14`); spec floor is 3 |

## Build & Test

Scores read from `scores.json` (per skill step 2 — not re-run):

```text
test_coverage = 0.77   → build + tests executed and passed (coverage 0.77 > 0)
defect_rate   = 1.0    → build+test succeeded
code_quality  = 0.8333
```

Test collection (read-only, for the R12 count only):

```text
python3 -m pytest --collect-only -q tests/
tests/test_api.py: 2   (test_health, test_crud_book)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 207 (main.py 125, models.py 36, test_api.py 46) |
| Files (.py source) | 3 |
| Dependencies | flask, sqlalchemy (+ pydantic imported in models.py) |
| Tests total | 2 |
| Tests effective | 2 |
| Skip ratio | 0% |
| Build/test | pass (test_coverage=0.77) |

## Findings

Full list in `findings.jsonl`:

1. [high] R12 — only 2 test functions collected; spec requires >= 3 (`tests/test_api.py:7,14`).

Note: `models.py` is dead code — `main.py` defines its own `Book` model and does not import
`models.py`. Not a spec violation, so not filed as a finding; surfaced for awareness.

## Reproduce

```bash
cd "experiments/adrianco/experiment-47-gptoss20b/bookshop/runs/agent=hermes-local_language=python_model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8_prompt=neutral_stack=gptoss/rep5"
cat scores.json                                  # stored build/test/quality scores
grep -rn "def test_" tests/ --include="*.py"     # 2 test functions
python3 -m pytest --collect-only -q tests/       # 2 collected items
```
